"""글 하나가 공부할 기술 소식인지 분류하고 학습 가치를 매긴다 — 요약과 같은 노트북 올라마 7.8B.

11-09 실측: 어제 AI 글 96건에 78초(글당 약 0.8초). 분류 기준은 모델이 판단하고, 틀린 사례는
코드 규칙이 아니라 학습 데이터로 고친다(루트 CLAUDE.md §5).
"""

from __future__ import annotations

import json
import os

import httpx

from news.adapter.outbound.llm.ollama_ko_summarizer import _base_url
from news.app.dtos.news_dtos import ArticleDto
from news.app.ports.output.news_digest_ports import (
    ArticleClassifierPort,
    ArticleJudgement,
    ClassifierUnavailableError,
)

DEFAULT_MODEL = "exaone3.5:7.8b"
LABELS = ("tech", "industry", "other")

SYSTEM_PROMPT = """너는 AI 엔지니어의 아침 소식을 고르는 편집자다. 독자의 목적은 새 AI 기술과 아키텍처를 공부하는 것이다.
글 하나를 분류하고 학습 가치를 매겨 JSON으로만 답한다. {"label":"...","value":1}
- tech: 새 모델 공개, 논문, 아키텍처, 학습·추론·에이전트 기법, 오픈소스 도구·릴리스, 벤치마크, 구현 경험과 분석
- industry: AI 관련이지만 투자, 인수, 인사, 시장, 정책, 행사, 제품 홍보 중심
- other: AI와 무관한 글, 어떤 모델이 좋은지 묻는 질문, 추천 요청, 하드웨어 구매 상담, 잡담
회사 소식 형식이어도 새 모델이나 기술을 공개한 글이면 tech다. 경영자 인터뷰와 사업 전략은 industry다.
value는 이 글을 읽어 새 기술을 얼마나 배울 수 있는지다.
- 5: 구체적인 기법, 아키텍처 설명, 실험 수치가 있다
- 3: 새 모델이나 도구를 소개하지만 기술 내용은 적다
- 1: 소개나 의견 중심이라 배울 내용이 거의 없다"""


def build_user_prompt(article: ArticleDto) -> str:
    summary = (article.summary_ko or article.summary)[:400]
    return (
        f"제목: {article.title_ko or article.title}\n원제: {article.title}\n"
        f"요약: {summary}\n출처: {article.source_name or article.source_domain}"
    )


class OllamaArticleClassifier(ArticleClassifierPort):
    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url or _base_url()
        self._model = model or os.getenv("NEWS_SUMMARY_MODEL") or DEFAULT_MODEL
        self._timeout = timeout
        self._transport = transport

    async def classify(self, article: ArticleDto) -> ArticleJudgement | None:
        body = {
            "model": self._model,
            "stream": False,
            "format": "json",
            "keep_alive": "2m",
            "options": {"temperature": 0, "num_predict": 40, "num_ctx": 4096},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(article)},
            ],
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                res = await client.post(f"{self._base_url}/api/chat", json=body)
        except httpx.HTTPError as e:
            raise ClassifierUnavailableError(f"{type(e).__name__}: {e}") from e
        if res.status_code >= 500 or res.status_code == 404:
            raise ClassifierUnavailableError(f"HTTP {res.status_code}")
        try:
            parsed = json.loads(res.json()["message"]["content"])
            label, value = parsed["label"], int(parsed["value"])
        except (ValueError, KeyError, TypeError):
            return None
        return ArticleJudgement(label, min(5, max(1, value))) if label in LABELS else None
