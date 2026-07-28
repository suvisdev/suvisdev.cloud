from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from silicon_valley.adapter.inbound.api.schemas.rangchain_chat_schema import (
    RangchainChatRequestSchema,
    RangchainChatResponseSchema,
)
from silicon_valley.app.ports.input.rangchain_chat_use_case import RangchainChatUseCase
from silicon_valley.app.ports.output.rangchain_chat_errors import RangchainChatError
from silicon_valley.dependencies.rangchain_chat_provider import get_rangchain_chat_use_case

rangchain_chat_router = APIRouter(prefix="/langchain", tags=["silicon-valley-langchain"])


@rangchain_chat_router.post("/chat", response_model=RangchainChatResponseSchema)
async def chat(
    req: RangchainChatRequestSchema,
    use_case: RangchainChatUseCase = Depends(get_rangchain_chat_use_case),
) -> RangchainChatResponseSchema:
    try:
        dto = await use_case.chat(
            messages=[m.model_dump() for m in req.messages],
            system=req.systemInstruction,
        )
    except RangchainChatError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return RangchainChatResponseSchema(reply=dto.reply)
