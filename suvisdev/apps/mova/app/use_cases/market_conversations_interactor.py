"""대화 스레드 Interactor — 목록·상세·삭제."""

from __future__ import annotations

from mova.app.dtos.market_conversations_dto import (
    ConversationDetailDto,
    ConversationSummaryDto,
)
from mova.app.ports.input.market_conversations_use_case import ConversationsUseCase
from mova.app.ports.output.market_conversations_errors import (
    ConversationForbiddenError,
    ConversationNotFoundError,
)
from mova.app.ports.output.market_conversations_repository import ConversationsRepository


class ConversationsInteractor(ConversationsUseCase):
    def __init__(self, repository: ConversationsRepository) -> None:
        self._repo = repository

    async def list_mine(self, user_id: int) -> list[ConversationSummaryDto]:
        return await self._repo.list_by_user(user_id)

    async def get_mine(self, conversation_id: int, user_id: int) -> ConversationDetailDto:
        await self._require_ownership(conversation_id, user_id)
        detail = await self._repo.get_detail(conversation_id)
        if detail is None:
            # 소유권 통과 후 사라진 경우(레이스). NotFound로 보고.
            raise ConversationNotFoundError()
        return detail

    async def delete_mine(self, conversation_id: int, user_id: int) -> None:
        await self._require_ownership(conversation_id, user_id)
        await self._repo.delete(conversation_id)

    async def _require_ownership(self, conversation_id: int, user_id: int) -> None:
        owner_id = await self._repo.get_owner_id(conversation_id)
        if owner_id is None:
            raise ConversationNotFoundError()
        if owner_id != user_id:
            raise ConversationForbiddenError()
