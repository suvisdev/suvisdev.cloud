"""LLM 추천 출력 포트 — 의도 추출·추천 생성 추상화 (DIP)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from mova.adapter.inbound.api.schemas.market_chat_schema import (
    MovaChatRecommendationSchema,
)
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema


class RecommendationPort(ABC):
    """LLM 기반 영화 추천 출력 포트.

    구체 LLM(Gemini 등)에 대한 의존을 역전시킨다. Interactor는 이 ABC에만
    의존하고, 구현체(GeminiRecommendationAdapter)는 `adapter/outbound/llm/`에 둔다.
    """

    @abstractmethod
    def extract_intent(self, message: str) -> dict[str, Any]:
        """사용자 메시지 → 검색 의도 dict.

        반환 키: refined_query · keywords · intent_type · search_filters.
        CPU-bound(형태소 분석)이라 동기 메서드 — 호출 측에서 asyncio.to_thread 위임.
        """

    @abstractmethod
    async def generate_recommendation(
        self,
        *,
        history: list[dict[str, str]],
        message: str,
        intent: dict[str, Any],
        tag_catalog: list[MovaSearchItemSchema],
        past_intents: list,
        user_nickname: str | None,
        preferred_genres: list[str],
        model: Literal["flash", "flash15", "pro"] | None,
    ) -> tuple[str, list[MovaChatRecommendationSchema]]:
        """의도·컨텍스트 → (응답 문구, 추천 작품 목록). I/O-bound(LLM 호출)."""
