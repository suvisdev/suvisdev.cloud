from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.app.dtos.receive_dto import ReceiveItem, ReceiveSaveCommand


class ReceivePort(ABC):
    @abstractmethod
    async def save(
        self, command: ReceiveSaveCommand, embedding: list[float] | None
    ) -> ReceiveItem: ...

    @abstractmethod
    async def list_all(self, limit: int) -> list[ReceiveItem]: ...

    @abstractmethod
    async def delete(self, item_id: int) -> None: ...
