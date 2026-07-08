from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.app.dtos.discord_dto import DiscordIntroduceQuery, DiscordIntroduceResponse


class DiscordPort(ABC):
    @abstractmethod
    def send(self, *, message: str, username: str | None) -> None: ...

    @abstractmethod
    async def introduce_myself(self, query: DiscordIntroduceQuery) -> DiscordIntroduceResponse: ...
