"""오케스트레이터 층의 데이터 객체(2026-09-27) — LLM이 읽어낸 발화(ChatUnderstanding)와
카탈로그·지도로 검증한 뒤의 슬롯(VerifiedSlots)을 구분한다. LLM은 이해만 하고 사실은
데이터가 확인한다는 원칙의 경계가 이 두 타입 사이다."""

from __future__ import annotations

from dataclasses import dataclass

from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema

INTENTS = ("recommend", "evaluate", "booking", "general")


@dataclass(frozen=True)
class ChatUnderstanding:
    """LLM 출력(정제 후). 어느 값도 아직 사실로 확인되지 않았다."""

    intent: str
    title: str | None = None
    region: str | None = None
    time: str | None = None
    chain: str | None = None
    followup: bool = False


@dataclass(frozen=True)
class VerifiedSlots:
    """검증을 거친 슬롯. `movie`는 카탈로그에서 확정된 작품, `title_text`는 LLM이 읽은 원문
    (카탈로그에 없으면 movie=None으로 남겨 트랙이 되묻는다). 지역은 카카오 지오코딩이
    예매 트랙 안에서 확인하므로 여기서는 문자열만 넘긴다."""

    intent: str
    title_text: str | None
    movie: MovaSearchItemSchema | None
    region: str | None
    time: str | None
    chain: str | None
    followup: bool
