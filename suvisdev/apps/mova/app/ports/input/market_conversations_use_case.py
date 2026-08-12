"""대화 스레드 입력 포트 — 라우터가 호출하는 유스케이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_conversations_dto import (
    ConversationDetailDto,
    ConversationSummaryDto,
)


class ConversationsUseCase(ABC):
    @abstractmethod
    async def list_mine(self, user_id: int) -> list[ConversationSummaryDto]:
        """본인의 대화 목록(사이드바)."""

    @abstractmethod
    async def get_mine(self, conversation_id: int, user_id: int) -> ConversationDetailDto:
        """본인 대화 상세. 소유자 아니면 ConversationForbiddenError.
        없으면 ConversationNotFoundError."""

    @abstractmethod
    async def delete_mine(self, conversation_id: int, user_id: int) -> None:
        """본인 대화 삭제. 소유자 아니면 ConversationForbiddenError.
        없으면 ConversationNotFoundError."""
