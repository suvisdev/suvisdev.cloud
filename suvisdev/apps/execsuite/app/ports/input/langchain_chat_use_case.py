from __future__ import annotations

from typing import Protocol

from execsuite.app.dtos.langchain_chat_dto import LangchainChatDto


class LangchainChatUseCase(Protocol):
    async def chat(
        self, *, messages: list[dict[str, str]], system: str | None
    ) -> LangchainChatDto: ...
