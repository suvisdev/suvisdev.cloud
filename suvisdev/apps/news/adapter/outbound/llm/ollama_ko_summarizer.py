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
from news.domain.feed_text import has_enough_text
from news.domain.ko_summary import KoSummary, is_korean, parse_ko_summary, parse_title_only

DEFAULT_MODEL = "exaone3.5:7.8b"
MAX_INPUT_CHARS = 1800

# 11-06 실측: "원문 그대로 둔다"만 쓰면 'Claude Opus 5'→"클레어 오퍼스 5", 'Kimi K3.1 Pro'→"김미 프로"로 옮겼다(16건 중 3건).
# 음역 금지와 예시를 넣으니 같은 16건에서 0건이 됐다.
_NAME_RULE = (
    "모델·회사·제품·코드 이름과 버전 번호는 번역하지도 한글로 음역하지도 말고 영어 글자 그대로 쓴다. "
    "Show HN·Ask HN·Tell HN 같은 말머리는 옮기지 않고 그대로 둔다.\n"
    "제목 예시\n"
    "Claude Code adds plugins → Claude Code에 플러그인 추가\n"
    "Kimi K3.1 Pro weights released → Kimi K3.1 Pro 가중치 공개\n"
    "Gemini 3.5 beats GPT-5.5 on coding → Gemini 3.5, 코딩에서 GPT-5.5 앞서\n"
)

SYSTEM_PROMPT = (
    "너는 AI 기술·경제 소식을 한국어로 정리하는 편집자다. 주어진 글의 제목을 자연스러운 한국어로 옮기고, "
    "내용을 한국어 2~3문장으로 요약한다. 무엇을 했는지와 핵심 결과·숫자를 먼저 쓴다. "
    "원문에 없는 사실이나 평가('중요한 발전', '혁신적' 같은 말)를 덧붙이지 않는다. "
    "제목이 이미 한국어면 그대로 둔다.\n"
    f"{_NAME_RULE}"
    '출력은 JSON 하나만: {"title_ko": "...", "summary_ko": "..."}'
)

TITLE_ONLY_PROMPT = (
    "너는 영어 기사 제목을 자연스러운 한국어로 옮기는 편집자다. 제목만 옮기고 내용을 덧붙이지 않는다.\n"
    f"{_NAME_RULE}"
    '출력은 JSON 하나만: {"title_ko": "..."}'
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
        if not has_enough_text(target.summary, target.body):
            return await self._title_only(target)
        content = await self._chat(SYSTEM_PROMPT, build_user_prompt(target), num_predict=400)
        return None if content is None else parse_ko_summary(content, target.title)

    async def _title_only(self, target: SummaryTarget) -> KoSummary | None:
        """요약할 내용이 없는 글(domain/feed_text.py) — 지어내지 않게 제목만 옮기고 요약은 비운다."""
        if is_korean(target.title):
            return KoSummary(title_ko=target.title, summary_ko="")
        content = await self._chat(TITLE_ONLY_PROMPT, f"제목: {target.title}", num_predict=120)
        return None if content is None else parse_title_only(content, target.title)

    async def _chat(self, system: str, user: str, *, num_predict: int) -> str | None:
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
        except httpx.HTTPError as e:  # 연결 실패·시간 초과
            raise SummarizerUnavailableError(f"{type(e).__name__}: {e}") from e
        if res.status_code >= 500 or res.status_code == 404:  # 서버 오류·모델 없음
            raise SummarizerUnavailableError(f"HTTP {res.status_code}")
        try:
            return str(res.json()["message"]["content"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None
