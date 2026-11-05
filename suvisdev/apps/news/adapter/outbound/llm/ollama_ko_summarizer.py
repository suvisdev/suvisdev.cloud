"""노트북 올라마 EXAONE 3.5 7.8B 로 한국어 제목·요약 (2026-11-05). 비용 0원.

11-05 노트북 RTX 4060 실측(실제 글 5건): 7.8B 글당 2.5~3.7초(첫 글은 모델 올리느라 12초), 영어 제목을 자연스럽게 옮김.
2.4B 는 1~5초로 빠르지만 영어 제목을 옮기지 않고 1건은 요약이 비어 나와 쓰지 않는다.
주소는 노트북 올라마를 직접 가리킨다(NEWS_SUMMARY_OLLAMA_URL → PORTFOLIO_LLM_OLLAMA_URL → OLLAMA_BASE_URL) —
중계기를 거치면 노트북 올라마가 죽었을 때 집컴 CPU(8.9GB)에 7.8B 를 올리게 된다(exaone_llm_adapter 와 같은 이유).
keep_alive 를 짧게 둬 mova 모델에 VRAM 을 돌려준다.
"""

from __future__ import annotations

import json
import os

import httpx

from news.app.dtos.news_dtos import SummaryTarget
from news.app.ports.output.news_summarizer_port import (
    ArticleSummarizerPort,
    SummarizerUnavailableError,
)
from news.domain.ko_summary import KoSummary, parse_ko_summary

DEFAULT_MODEL = "exaone3.5:7.8b"
MAX_INPUT_CHARS = 1800

SYSTEM_PROMPT = (
    "너는 AI 기술·경제 소식을 한국어로 정리하는 편집자다. 주어진 글의 제목을 자연스러운 한국어로 옮기고, "
    "내용을 한국어 2~3문장으로 요약한다. 무엇을 했는지와 핵심 결과·숫자를 먼저 쓴다. "
    "원문에 없는 사실이나 평가('중요한 발전', '혁신적' 같은 말)를 덧붙이지 않는다. "
    "모델·회사·제품·코드 이름과 숫자는 원문 그대로 둔다. 제목이 이미 한국어면 그대로 둔다. "
    '출력은 JSON 하나만: {"title_ko": "...", "summary_ko": "..."}'
)


def _base_url() -> str:
    return (
        os.getenv("NEWS_SUMMARY_OLLAMA_URL")
        or os.getenv("PORTFOLIO_LLM_OLLAMA_URL")
        or os.getenv("OLLAMA_BASE_URL")
        or "http://localhost:11434"
    ).rstrip("/")


def build_user_prompt(target: SummaryTarget) -> str:
    text = target.summary
    if target.body and target.body[:200] not in text:
        text = f"{text}\n{target.body}"
    return f"제목: {target.title}\n출처: {target.source_name or ''}\n내용: {text[:MAX_INPUT_CHARS]}"


class OllamaKoSummarizer(ArticleSummarizerPort):
    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 90.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url or _base_url()
        self._model: str = model or os.getenv("NEWS_SUMMARY_MODEL") or DEFAULT_MODEL
        self._timeout = timeout
        self._transport = transport

    @property
    def model_name(self) -> str:
        return self._model

    async def summarize(self, target: SummaryTarget) -> KoSummary | None:
        body = {
            "model": self._model,
            "stream": False,
            "format": "json",
            "keep_alive": "2m",
            "options": {"temperature": 0.2, "num_predict": 400, "num_ctx": 4096},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(target)},
            ],
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                res = await client.post(f"{self._base_url}/api/chat", json=body)
        except httpx.HTTPError as e:  # 연결 실패·시간 초과
            raise SummarizerUnavailableError(f"{type(e).__name__}: {e}") from e
        if res.status_code >= 500 or res.status_code == 404:  # 서버 오류·모델 없음
            raise SummarizerUnavailableError(f"HTTP {res.status_code}")
        try:
            content = str(res.json()["message"]["content"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None
        return parse_ko_summary(content, target.title)
