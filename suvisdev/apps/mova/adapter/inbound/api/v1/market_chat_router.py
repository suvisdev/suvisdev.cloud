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
from mova.dependencies.market_chat_provider import get_chat_use_case

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
    use_case: ChatUseCase = Depends(get_chat_use_case),
    _rate: None = Depends(chat_rate_limit),
) -> MovaChatResponseSchema:
    """사용자 메시지 → 의도 추출 → Gemini 추천 → picks 저장."""
    try:
        dto = await use_case.chat(req)
    except LLMError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return dto.to_schema()
