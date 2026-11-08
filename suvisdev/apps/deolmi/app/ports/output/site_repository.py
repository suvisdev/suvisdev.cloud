from __future__ import annotations

from abc import ABC, abstractmethod

from deolmi.app.dtos.site_dto import SiteCreateCommand, SiteDto


class SiteLookupPort(ABC):
    """채점·검증이 쓰는 키 조회만."""

    @abstractmethod
    async def get_active(self, site_key: str) -> SiteDto | None: ...


class SiteRepositoryPort(SiteLookupPort):
    """조회 + 어드민용 발급·목록."""

    @abstractmethod
    async def create(
        self, command: SiteCreateCommand, site_key: str, secret_hash: str
    ) -> SiteDto: ...

    @abstractmethod
    async def list_all(self) -> list[SiteDto]: ...
