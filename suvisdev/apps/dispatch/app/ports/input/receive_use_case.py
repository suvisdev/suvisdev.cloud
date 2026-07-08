from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.app.dtos.receive_dto import ReceiveItem, ReceiveSaveCommand


class ReceiveUseCase(ABC):
    @abstractmethod
    async def save(self, command: ReceiveSaveCommand) -> ReceiveItem: ...

    @abstractmethod
    async def list_all(self, limit: int) -> list[ReceiveItem]: ...

    @abstractmethod
    async def delete(self, item_id: int) -> None: ...
