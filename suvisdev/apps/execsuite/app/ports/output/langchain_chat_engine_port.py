from __future__ import annotations

from typing import Protocol


class LangchainChatEnginePort(Protocol):
    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        destination: str,
        entities: list[str],
        grounding: str,
    ) -> str: ...
