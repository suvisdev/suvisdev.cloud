from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from shared.security.require_admin import AdminPrincipal, require_admin

from execsuite.adapter.inbound.api.schemas.langchain_chat_schema import (
    LangchainChatRequestSchema,
    LangchainChatResponseSchema,
)
from execsuite.app.ports.input.langchain_chat_use_case import LangchainChatUseCase
from execsuite.app.ports.output.langchain_chat_errors import LangchainChatError
from execsuite.dependencies.langchain_chat_provider import get_langchain_chat_use_case

langchain_chat_router = APIRouter(prefix="/langchain", tags=["execsuite-langchain"])


@langchain_chat_router.post("/chat", response_model=LangchainChatResponseSchema)
async def chat(
    req: LangchainChatRequestSchema,
    use_case: LangchainChatUseCase = Depends(get_langchain_chat_use_case),
    _: AdminPrincipal = Depends(require_admin),
) -> LangchainChatResponseSchema:
    try:
        dto = await use_case.chat(
            messages=[m.model_dump() for m in req.messages],
            system=req.systemInstruction,
        )
    except LangchainChatError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return LangchainChatResponseSchema(reply=dto.reply)
