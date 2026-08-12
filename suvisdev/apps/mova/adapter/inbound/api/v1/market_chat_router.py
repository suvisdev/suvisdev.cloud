"""채팅 라우터 — POST /mova/chat"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mova.adapter.inbound.api.rate_limit import chat_rate_limit
from mova.adapter.inbound.api.schemas.market_chat_schema import (
    MovaChatRequest,
    MovaChatResponseSchema,
)
from mova.app.ports.input.market_chat_use_case import ChatUseCase
from mova.app.ports.output.llm_errors import LLMError
from mova.app.ports.output.market_conversations_errors import (
    ConversationForbiddenError,
    ConversationNotFoundError,
)
from mova.dependencies.market_chat_provider import get_chat_use_case
from shared.security.require_user import UserPrincipal, optional_user

market_chat_router = APIRouter(prefix="/chat", tags=["mova-chat"])


class _MyselfResponse(BaseModel):
    id: int
    name: str


@market_chat_router.get("/myself", response_model=_MyselfResponse)
async def introduce_myself() -> _MyselfResponse:
    return _MyselfResponse(id=1, name="시나리오 작가 (Screenwriter)")


@market_chat_router.post("", response_model=MovaChatResponseSchema)
async def chat(
    req: MovaChatRequest,
    principal: UserPrincipal | None = Depends(optional_user),
    use_case: ChatUseCase = Depends(get_chat_use_case),
    _rate: None = Depends(chat_rate_limit),
) -> MovaChatResponseSchema:
    """사용자 메시지 → 의도 추출 → Gemini 추천 → picks 저장.

    비로그인 사용은 그대로 허용한다(익명 = `user_id` None). 다만 **요청 바디의
    `user_id`는 신뢰하지 않는다** — 예전엔 임의의 user_id를 넣으면 그 사람의
    과거 대화·선호로 개인화된 답을 받고, 그 사람의 대화·추천 이력에 기록까지
    남길 수 있었다(2026-08-07 수정). 신원은 토큰에서만 온다.
    """
    req = req.model_copy(update={"user_id": principal.user_id if principal else None})
    try:
        dto = await use_case.chat(req)
    except LLMError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except (ConversationNotFoundError, ConversationForbiddenError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return dto.to_schema()
