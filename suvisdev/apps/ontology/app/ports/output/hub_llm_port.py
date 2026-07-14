from __future__ import annotations

from abc import ABC, abstractmethod


class HubLlmPort(ABC):
    @abstractmethod
    async def generate(self, prompt: str, *, system: str | None = None) -> str: ...
