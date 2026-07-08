from __future__ import annotations

from dispatch.adapter.inbound.api.schemas.discord_schema import DiscordIntroduceSchema
from dispatch.app.dtos.discord_dto import (
    DiscordDto,
    DiscordIntroduceQuery,
    DiscordIntroduceResponse,
)
from dispatch.app.ports.input.discord_use_case import DiscordUseCase
from dispatch.app.ports.output.discord_port import DiscordPort
from dispatch.app.ports.output.dispatch_errors import DispatchError


class SendDiscordInteractor(DiscordUseCase):
    def __init__(self, *, discord: DiscordPort) -> None:
        self._discord = discord

    def send(self, *, message: str, username: str | None) -> DiscordDto:
        try:
            self._discord.send(message=message, username=username)
        except DispatchError:
            raise
        return DiscordDto(success=True)

    async def introduce_myself(self, schema: DiscordIntroduceSchema) -> DiscordIntroduceResponse:
        return await self._discord.introduce_myself(
            DiscordIntroduceQuery(id=schema.id, name=schema.name)
        )
