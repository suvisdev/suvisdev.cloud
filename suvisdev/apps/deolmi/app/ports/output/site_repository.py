from __future__ import annotations

from abc import ABC, abstractmethod

from deolmi.app.dtos.site_dto import SiteCreateCommand, SiteDto


class SiteRepositoryPort(ABC):
    @abstractmethod
    async def get_active(self, site_key: str) -> SiteDto | None: ...

    @abstractmethod
    async def create(
        self, command: SiteCreateCommand, site_key: str, secret_hash: str
    ) -> SiteDto: ...

    @abstractmethod
    async def list_all(self) -> list[SiteDto]: ...
