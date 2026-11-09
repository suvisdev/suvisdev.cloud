from __future__ import annotations

from abc import ABC, abstractmethod

from deolmi.app.dtos.site_dto import IssuedSiteDto, SiteCreateCommand, SiteDto, StatsDto


class SiteAdminUseCase(ABC):
    @abstractmethod
    async def create_site(self, command: SiteCreateCommand) -> IssuedSiteDto: ...

    @abstractmethod
    async def list_sites(self) -> list[SiteDto]: ...

    @abstractmethod
    async def set_site_active(self, site_key: str, active: bool) -> SiteDto: ...

    @abstractmethod
    async def rotate_secret(self, site_key: str) -> IssuedSiteDto: ...

    @abstractmethod
    async def stats(self) -> StatsDto: ...
