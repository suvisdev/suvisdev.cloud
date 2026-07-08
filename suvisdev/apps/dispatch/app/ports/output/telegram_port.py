from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.app.dtos.telegram_dto import TelegramIntroduceQuery, TelegramIntroduceResponse


class TelegramPort(ABC):
    @abstractmethod
    def send(self, *, message: str, chat_id: str) -> None: ...

    @abstractmethod
    async def introduce_myself(
        self, query: TelegramIntroduceQuery
    ) -> TelegramIntroduceResponse: ...
