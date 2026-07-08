from __future__ import annotations

from dispatch.adapter.inbound.api.schemas.telegram_schema import TelegramIntroduceSchema
from dispatch.app.dtos.telegram_dto import (
    TelegramDto,
    TelegramIntroduceQuery,
    TelegramIntroduceResponse,
)
from dispatch.app.ports.input.telegram_use_case import TelegramUseCase
from dispatch.app.ports.output.dispatch_errors import DispatchError
from dispatch.app.ports.output.telegram_port import TelegramPort


class SendTelegramInteractor(TelegramUseCase):
    def __init__(self, *, telegram: TelegramPort, default_chat_id: str) -> None:
        self._telegram = telegram
        self._default_chat_id = default_chat_id

    def send(self, *, message: str, chat_id: str | None) -> TelegramDto:
        resolved = (chat_id or self._default_chat_id).strip()
        if not resolved:
            raise DispatchError("TELEGRAM_CHAT_ID가 설정되지 않았습니다.", status_code=503)
        try:
            self._telegram.send(message=message, chat_id=resolved)
        except DispatchError:
            raise
        return TelegramDto(success=True)

    async def introduce_myself(self, schema: TelegramIntroduceSchema) -> TelegramIntroduceResponse:
        return await self._telegram.introduce_myself(
            TelegramIntroduceQuery(id=schema.id, name=schema.name)
        )
