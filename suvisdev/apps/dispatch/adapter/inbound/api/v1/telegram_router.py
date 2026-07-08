from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dispatch.adapter.inbound.api.schemas.telegram_schema import (
    TelegramIntroduceSchema,
    TelegramRequest,
    TelegramResponseSchema,
)
from dispatch.app.dtos.telegram_dto import TelegramIntroduceResponse
from dispatch.app.ports.input.telegram_use_case import TelegramUseCase
from dispatch.app.ports.output.dispatch_errors import DispatchError
from dispatch.dependencies.telegram_provider import get_telegram_use_case

telegram_router = APIRouter(prefix="/telegram", tags=["dispatch-telegram"])


@telegram_router.get("/myself")
async def introduce_myself(
    use_case: TelegramUseCase = Depends(get_telegram_use_case),
) -> TelegramIntroduceResponse:
    return await use_case.introduce_myself(TelegramIntroduceSchema(id=4, name="Telegram 발송"))


@telegram_router.post("", response_model=TelegramResponseSchema)
def send_telegram(
    req: TelegramRequest,
    use_case: TelegramUseCase = Depends(get_telegram_use_case),
) -> TelegramResponseSchema:
    try:
        dto = use_case.send(message=req.message, chat_id=req.chat_id)
    except DispatchError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return TelegramResponseSchema(success=dto.success)
