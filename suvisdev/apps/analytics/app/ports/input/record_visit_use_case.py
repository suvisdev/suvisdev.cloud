from __future__ import annotations

from abc import ABC, abstractmethod


class RecordVisitUseCase(ABC):
    @abstractmethod
    async def record(self, visitor_id: str, user_agent: str | None = None) -> None: ...
