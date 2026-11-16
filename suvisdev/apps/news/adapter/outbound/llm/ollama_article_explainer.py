"""메일 기사 풀이·분석과 오늘의 흐름 — 요약·분류와 같은 노트북 올라마 7.8B(11-16 사용자 선택).

11-16 실측(실제 글 5건): 글당 7.5~13초. 첫 지시문은 단점을 "프라이버시·편향" 같은 일반론으로 채우고(강수 데이터 글),
지시문의 '~할 수 있다'를 답에 그대로 옮겨 적어 아래처럼 고쳤다. 틀린 풀이는 코드 규칙이 아니라 학습 데이터로 고친다(루트 CLAUDE.md §5).
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any

import httpx

from news.adapter.outbound.llm.ollama_ko_summarizer import _base_url
from news.app.ports.output.news_digest_ports import (
    ArticleExplainerPort,
    ClassifierUnavailableError,
)
from news.domain.digest import DigestItem, Explanation

DEFAULT_MODEL = "exaone3.5:7.8b"
MAX_POINTS = 3

EXPLAIN_PROMPT = """너는 AI 기술 소식을 쉽게 풀어 주고 분석하는 해설자다. 독자는 AI 엔지니어를 준비하는 사람이다.
기사를 읽고 JSON 하나로만 답한다. {"easy":"...","why":"...","pros":["..."],"cons":["..."]}
- easy: 무슨 일인지 전문 용어 없이 2~3문장. 꼭 필요한 용어는 괄호 안에 쉬운 말로 푼다.
- why: 왜 중요한지, 누구에게 어떤 변화가 생기는지 1~2문장.
- pros: 이 기술이나 결정의 이점 2~3개, 각 한 문장.
- cons: 단점, 한계, 위험, 아직 검증 안 된 점 2~3개, 각 한 문장.
단점은 이 기사의 기술과 상황에 맞는 것만 쓴다. 기사와 상관없는 일반론(개인정보, 편향, 보안 등)은 그 기사가 실제로 그런 데이터나 위험을 다룰 때만 쓴다.
기사에 근거가 없는 단점은 단정하지 말고 추정하는 말투로 쓴다.
기사에 나온 숫자와 이름만 쓰고 없는 숫자·사실은 지어내지 않는다. 모델·회사·제품 이름은 영어 글자 그대로 쓴다."""

TREND_PROMPT = """너는 AI 기술 소식 편집자다. 오늘 고른 기사 목록을 보고 오늘 어떤 흐름이 있었는지 한국어 3줄로 정리한다.
각 줄은 한 문장이고, 여러 기사에 걸친 공통점이나 눈에 띄는 변화를 쓴다. 목록에 없는 사실은 쓰지 않는다.
JSON 하나로만 답한다. {"trend":["...","...","..."]}"""


def build_explain_prompt(item: DigestItem, page_text: str) -> str:
    source = f"원문:\n{page_text}" if page_text else "원문: (못 읽음 — 요약만 보고 쓴다)"
    return f"제목: {item.title}\n출처: {item.source}\n요약: {item.summary}\n{source}"


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(s.strip() for s in value if isinstance(s, str) and s.strip())[:MAX_POINTS]


def parse_explanation(parsed: dict[str, Any], *, from_page: bool) -> Explanation | None:
    """모델 JSON → 풀이. 핵심인 easy 가 없으면 None(그 기사는 풀이 없이 보낸다)."""
    easy, why = parsed.get("easy"), parsed.get("why")
    if not isinstance(easy, str) or not easy.strip():
        return None
    return Explanation(
        easy=easy.strip(),
        why=why.strip() if isinstance(why, str) else "",
        pros=_strings(parsed.get("pros")),
        cons=_strings(parsed.get("cons")),
        from_page=from_page,
    )


class OllamaArticleExplainer(ArticleExplainerPort):
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

    async def explain(self, item: DigestItem, page_text: str) -> Explanation | None:
        parsed = await self._chat(EXPLAIN_PROMPT, build_explain_prompt(item, page_text), 700)
        return parse_explanation(parsed, from_page=bool(page_text))

    async def trend(self, items: Sequence[DigestItem]) -> list[str]:
        lines = "\n".join(
            f"- {i.title}: {i.explanation.easy if i.explanation else i.summary}" for i in items
        )
        return list(_strings((await self._chat(TREND_PROMPT, lines, 300)).get("trend")))

    async def _chat(self, system: str, user: str, num_predict: int) -> dict[str, Any]:
        body = {
            "model": self._model,
            "stream": False,
            "format": "json",
            "keep_alive": "2m",
            "options": {"temperature": 0.2, "num_predict": num_predict, "num_ctx": 4096},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
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
        except (ValueError, KeyError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
