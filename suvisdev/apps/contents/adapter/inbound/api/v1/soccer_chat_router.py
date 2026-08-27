from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from shared.security.require_admin import AdminPrincipal, require_admin

from contents.adapter.inbound.api.schemas.soccer_chat_schema import (
    SoccerChatRequestSchema,
    SoccerChatResponseSchema,
)
from contents.app.ports.input.soccer_chat_use_case import SoccerChatUseCase
from contents.app.ports.output.soccer_chat_errors import SoccerChatError
from contents.dependencies.soccer_chat_provider import get_soccer_chat_use_case

soccer_chat_router = APIRouter(prefix="/soccer", tags=["contents-soccer"])


@soccer_chat_router.post("/chat", response_model=SoccerChatResponseSchema)
def chat(
    req: SoccerChatRequestSchema,
    use_case: SoccerChatUseCase = Depends(get_soccer_chat_use_case),
    _: AdminPrincipal = Depends(require_admin),
) -> SoccerChatResponseSchema:
    try:
        dto = use_case.chat(
            messages=[m.model_dump() for m in req.messages],
            system=req.systemInstruction,
        )
    except SoccerChatError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return SoccerChatResponseSchema(reply=dto.reply)
