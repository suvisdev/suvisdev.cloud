"""대화 스레드 라우터 — /mova/conversations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from shared.security.require_user import UserPrincipal, require_user

from mova.adapter.inbound.api.schemas.market_conversations_schema import (
    ConversationDetailSchema,
    ConversationSummarySchema,
)
from mova.app.ports.input.market_conversations_use_case import ConversationsUseCase
from mova.app.ports.output.market_conversations_errors import (
    ConversationForbiddenError,
    ConversationNotFoundError,
)
from mova.dependencies.market_conversations_provider import get_conversations_use_case

market_conversations_router = APIRouter(prefix="/conversations", tags=["mova-conversations"])


@market_conversations_router.get("", response_model=list[ConversationSummarySchema])
async def list_conversations(
    principal: UserPrincipal = Depends(require_user),
    use_case: ConversationsUseCase = Depends(get_conversations_use_case),
) -> list[ConversationSummarySchema]:
    """본인 대화 목록(사이드바). updated_at DESC 정렬."""
    dtos = await use_case.list_mine(principal.user_id)
    return [d.to_schema() for d in dtos]


@market_conversations_router.get("/{conversation_id}", response_model=ConversationDetailSchema)
async def get_conversation(
    conversation_id: int,
    principal: UserPrincipal = Depends(require_user),
    use_case: ConversationsUseCase = Depends(get_conversations_use_case),
) -> ConversationDetailSchema:
    """대화 상세 + 메시지 전체. 본인 소유만."""
    try:
        dto = await use_case.get_mine(conversation_id, principal.user_id)
    except (ConversationNotFoundError, ConversationForbiddenError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return dto.to_schema()


@market_conversations_router.delete("/{conversation_id}", status_code=200)
async def delete_conversation(
    conversation_id: int,
    principal: UserPrincipal = Depends(require_user),
    use_case: ConversationsUseCase = Depends(get_conversations_use_case),
) -> dict[str, str]:
    """대화 삭제(메시지 CASCADE). 본인 소유만."""
    try:
        await use_case.delete_mine(conversation_id, principal.user_id)
    except (ConversationNotFoundError, ConversationForbiddenError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return {"status": "deleted"}
