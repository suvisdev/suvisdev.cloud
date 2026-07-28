from __future__ import annotations

from typing import Protocol

from execsuite.app.dtos.rangchain_chat_dto import RangchainChatDto


class RangchainChatUseCase(Protocol):
    async def chat(
        self, *, messages: list[dict[str, str]], system: str | None
    ) -> RangchainChatDto: ...
