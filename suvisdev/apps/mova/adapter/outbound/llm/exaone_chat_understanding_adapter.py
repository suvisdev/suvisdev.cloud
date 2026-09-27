"""ChatUnderstandingPort 구현 — EXAONE(Ollama, core.lol SuvisdevOrchestrator)로 슬롯 추출.

2026-09-27 실측(노트북 RTX 4060, 발화 6건):
  exaone3.5:2.4b  평균 0.87s — 제목을 못 뽑고 스키마 문자열("시각/날짜 표현")을 그대로 뱉음 → 불가
  exaone3.5:7.8b  평균 0.85s(예열 후, 첫 호출 7s) — 파과·인턴·"군자" 이어받기·옵세션 evaluate 정확
모델은 MOVA_ORCHESTRATOR_MODEL로 바꾼다. 출력은 JSON 모드로 받고, 값은 아래 _clean이 정제한다 —
LLM은 "없음"·"null"·스키마 문구·발화에 없는 체인명을 섞어 내므로 그대로 믿지 않는다.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

from core.lol.suvisdev_orchestrator import (
    SuvisdevOrchestrator,
    SuvisdevOrchestratorError,
    _parse_json_object,
)
from mova.app.dtos.chat_understanding_dto import INTENTS, ChatUnderstanding
from mova.app.ports.output.chat_understanding_port import (
    ChatUnderstandingError,
    ChatUnderstandingPort,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "exaone3.5:7.8b"
_HISTORY_TURNS = 4
_HISTORY_CHARS = 160

SYSTEM_PROMPT = """너는 영화 챗봇 mova의 '이해 담당'이다. 사용자 발화와 최근 대화를 읽고 아래 JSON 한 개만 출력한다. 설명·인사 금지.
{"intent":"recommend|evaluate|booking|general","title":작품명 또는 null,"region":지역명 또는 null,"time":시각·날짜 표현 또는 null,"chain":"CGV"|"롯데시네마"|"메가박스"|null,"followup":true|false}

intent 기준:
- booking: 예매·예약·상영관·영화관·극장·시간표·회차·"몇 시"·"어디서 볼 수 있"·체인명이 있거나, 특정 작품을 극장에서 보려는 뜻.
- evaluate: 특정 작품이 어떤지 묻는 것("어때", "볼만해", "평점", "리뷰", "줄거리").
- recommend: 볼 영화를 골라 달라는 것("추천", "뭐 볼까", 장르·분위기·배우로 찾기).
- general: 영화와 무관한 인사·잡담·일반 질문.

값 규칙:
- title은 발화(또는 이어받는 직전 대화)에 실제로 나온 작품명만, 조사 없이 그대로. 없으면 null. 지어내지 않는다.
- region은 지역·역·동 이름만("군자", "강남역"). 없으면 null.
- chain은 발화에 그 체인명이 직접 나올 때만.
- followup: 직전 대화에 이어지는 짧은 답(지역만 말함, "그거", "26년꺼")이면 true이고 title은 직전 대화의 작품.

예시:
발화 "파과 예매할 수 있게 시간봐줘 그럼" → {"intent":"booking","title":"파과","region":null,"time":null,"chain":null,"followup":false}
발화 "군자에서 인턴 오늘 몇 시에 볼 수 있어?" → {"intent":"booking","title":"인턴","region":"군자","time":"오늘","chain":null,"followup":false}
직전 도우미 "『인턴』 어느 지역에서 보실 계획인가요?" · 발화 "군자" → {"intent":"booking","title":"인턴","region":"군자","time":null,"chain":null,"followup":true}
발화 "옵세션 어때?" → {"intent":"evaluate","title":"옵세션","region":null,"time":null,"chain":null,"followup":false}
발화 "요즘 볼만한 코미디 추천해줘" → {"intent":"recommend","title":null,"region":null,"time":null,"chain":null,"followup":false}
발화 "안녕" → {"intent":"general","title":null,"region":null,"time":null,"chain":null,"followup":false}"""

_NULLISH = frozenset({"", "null", "none", "없음", "없다", "미정", "n/a", "-"})
_SCHEMA_ECHO = re.compile(r"작품명|지역명|시각|날짜 표현|또는|\|")
_CHAINS = ("CGV", "롯데시네마", "메가박스")


def _clean_str(
    value: Any, message: str, *, must_appear_in: tuple[str, ...] | None = None
) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.strip().strip("'\"『』")
    if v.lower() in _NULLISH or _SCHEMA_ECHO.search(v):
        return None
    if must_appear_in is not None and not any(c in message for c in must_appear_in):
        return None
    return v or None


def parse_understanding(data: dict[str, Any] | str, message: str) -> ChatUnderstanding:
    """LLM 출력(dict 또는 JSON 문자열) → ChatUnderstanding. 형식이 아니면 ChatUnderstandingError."""
    if isinstance(data, str):
        parsed = _parse_json_object(data)
        if parsed is None:
            raise ChatUnderstandingError(f"JSON 아님: {data[:120]}")
        data = parsed
    intent = str(data.get("intent") or "").strip().lower()
    if intent not in INTENTS:
        raise ChatUnderstandingError(f"알 수 없는 intent: {intent!r}")
    chain = _clean_str(data.get("chain"), message, must_appear_in=_CHAINS)
    if chain is not None and chain not in _CHAINS:
        chain = next((c for c in _CHAINS if c in message), None)
    return ChatUnderstanding(
        intent=intent,
        title=_clean_str(data.get("title"), message),
        region=_clean_str(data.get("region"), message),
        time=_clean_str(data.get("time"), message),
        chain=chain,
        followup=bool(data.get("followup")) if isinstance(data.get("followup"), bool) else False,
    )


def _render_history(history: list[dict[str, str]]) -> str:
    lines = []
    for m in history[-_HISTORY_TURNS:]:
        content = (m.get("content") or "").strip()
        if not content:
            continue
        who = "사용자" if m.get("role") == "user" else "도우미"
        lines.append(f"{who}: {content[:_HISTORY_CHARS]}")
    return "\n".join(lines)


class ExaoneChatUnderstandingAdapter(ChatUnderstandingPort):
    def __init__(self, client: SuvisdevOrchestrator | None = None) -> None:
        self._client = client or SuvisdevOrchestrator(
            model=os.getenv("MOVA_ORCHESTRATOR_MODEL", _DEFAULT_MODEL),
            timeout=float(os.getenv("MOVA_ORCHESTRATOR_TIMEOUT_S", "20")),
        )

    async def understand(self, message: str, history: list[dict[str, str]]) -> ChatUnderstanding:
        rendered = _render_history(history)
        prompt = (f"[최근 대화]\n{rendered}\n\n" if rendered else "") + f"[발화]\n{message}"
        try:
            # 동기 httpx 클라이언트 — 이벤트 루프를 막지 않게 스레드로 넘긴다.
            data = await asyncio.to_thread(
                self._client.understand_json, prompt, system=SYSTEM_PROMPT, num_ctx=2048
            )
        except SuvisdevOrchestratorError as e:
            raise ChatUnderstandingError(e.detail) from e
        return parse_understanding(data, message)
