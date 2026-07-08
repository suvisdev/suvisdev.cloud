from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.app.dtos.adress_dto import (
    AdressCommand,
    AdressIntroduceQuery,
    AdressIntroduceResponse,
    AdressSearchQuery,
    AdressSearchResult,
)


class AdressPort(ABC):
    @abstractmethod
    async def bulk_save(self, commands: list[AdressCommand]) -> int: ...

    @abstractmethod
    async def introduce_myself(self, query: AdressIntroduceQuery) -> AdressIntroduceResponse: ...

    @abstractmethod
    async def search(self, query: AdressSearchQuery) -> list[AdressSearchResult]: ...
