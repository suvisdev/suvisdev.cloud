"""대화 스레드 리포지토리 포트 — 스레드·메시지 CRUD."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mova.app.dtos.market_conversations_dto import (
    ConversationDetailDto,
    ConversationSummaryDto,
)


class ConversationsRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: int) -> list[ConversationSummaryDto]:
        """updated_at DESC, 사이드바용."""

    @abstractmethod
    async def get_owner_id(self, conversation_id: int) -> int | None:
        """소유권 검증용 — 없으면 None."""

    @abstractmethod
    async def get_detail(self, conversation_id: int) -> ConversationDetailDto | None:
        """스레드 + 메시지 전체(오래된→최신 순)."""

    @abstractmethod
    async def create(self, user_id: int, title: str) -> int:
        """새 대화 생성 → id 반환."""

    @abstractmethod
    async def append_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        meta: dict[str, Any],
    ) -> None:
        """메시지 append + 부모 conversation updated_at 갱신."""

    @abstractmethod
    async def delete(self, conversation_id: int) -> None:
        """CASCADE로 메시지도 함께 지워진다."""
