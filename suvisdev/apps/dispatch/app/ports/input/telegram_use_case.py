from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.adapter.inbound.api.schemas.telegram_schema import TelegramIntroduceSchema
from dispatch.app.dtos.telegram_dto import TelegramDto, TelegramIntroduceResponse


class TelegramUseCase(ABC):
    @abstractmethod
    def send(self, *, message: str, chat_id: str | None) -> TelegramDto: ...

    @abstractmethod
    async def introduce_myself(
        self, schema: TelegramIntroduceSchema
    ) -> TelegramIntroduceResponse: ...
