from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.adapter.inbound.api.schemas.discord_schema import DiscordIntroduceSchema
from dispatch.app.dtos.discord_dto import DiscordDto, DiscordIntroduceResponse


class DiscordUseCase(ABC):
    @abstractmethod
    def send(self, *, message: str, username: str | None) -> DiscordDto: ...

    @abstractmethod
    async def introduce_myself(
        self, schema: DiscordIntroduceSchema
    ) -> DiscordIntroduceResponse: ...
