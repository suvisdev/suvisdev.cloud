from __future__ import annotations

from typing import Protocol

from silicon_valley.app.dtos.rangchain_chat_dto import RangchainChatDto


class RangchainChatUseCase(Protocol):
    async def chat(
        self, *, messages: list[dict[str, str]], system: str | None
    ) -> RangchainChatDto: ...
