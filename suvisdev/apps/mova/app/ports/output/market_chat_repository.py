"""채팅 출력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from mova.adapter.inbound.api.schemas.market_chat_schema import (
    MovaChatRecommendationSchema,
)
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema


class ChatRepositoryPort(ABC):
    @abstractmethod
    async def search_tag_catalog(
        self, keywords: list[str], limit: int
    ) -> list[MovaSearchItemSchema]:
        """keywords로 tags.label ILIKE → 영화 목록 카탈로그."""

    @abstractmethod
    async def get_recent_intents_by_user(self, user_id: int, limit: int) -> list:
        """사용자 최근 검색 의도 (MovaChat rows)."""

    @abstractmethod
    async def save_chat(
        self,
        *,
        user_id: int | None,
        assistant_id: int | None,
        raw_message: str,
        refined_query: str,
        keywords: list[str],
        intent_type: str,
        search_filters: dict,
    ) -> int:
        """chat 저장 → chat.id 반환."""

    @abstractmethod
    async def save_picks(
        self,
        *,
        chat_id: int,
        user_id: int | None,
        recommendations: list[MovaChatRecommendationSchema],
        batch_at: datetime,
    ) -> None:
        """picks 저장 (slug → movie_id 조회 포함)."""
