from __future__ import annotations

from deolmi.app.dtos.site_dto import IssuedSiteDto, SiteCreateCommand, SiteDto, StatsDto
from deolmi.app.ports.input.site_admin_use_case import SiteAdminUseCase
from deolmi.app.ports.output.anomaly_model_port import AnomalyModelPort
from deolmi.app.ports.output.event_repository import EventRepositoryPort
from deolmi.app.ports.output.site_repository import SiteRepositoryPort
from deolmi.domain.services.site_keys import hash_secret, new_secret_key, new_site_key


class SiteAdminInteractor(SiteAdminUseCase):
    """운영자용 — 고객 키 발급·목록·통계."""

    def __init__(
        self,
        sites: SiteRepositoryPort,
        events: EventRepositoryPort,
        model: AnomalyModelPort,
    ) -> None:
        self._sites = sites
        self._events = events
        self._model = model

    async def create_site(self, command: SiteCreateCommand) -> IssuedSiteDto:
        secret_key = new_secret_key()
        site = await self._sites.create(command, new_site_key(), hash_secret(secret_key))
        return IssuedSiteDto(site=site, secret_key=secret_key)

    async def list_sites(self) -> list[SiteDto]:
        return await self._sites.list_all()

    async def stats(self) -> StatsDto:
        return StatsDto(
            event_count=await self._events.count(),
            model_source=self._model.source,
            recent=await self._events.recent(20),
        )
