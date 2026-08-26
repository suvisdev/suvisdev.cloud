from __future__ import annotations

from typing import Protocol

from contents.app.dtos.soccer_chat_dto import SoccerChatDto


class SoccerChatUseCase(Protocol):
    def chat(self, *, messages: list[dict[str, str]], system: str | None) -> SoccerChatDto: ...
