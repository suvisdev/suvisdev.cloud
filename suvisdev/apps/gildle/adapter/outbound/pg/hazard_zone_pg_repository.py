from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from gildle.adapter.outbound.orm.hazard_zone_orm import HazardZoneOrm
from gildle.app.ports.output.hazard_zone_repository import HazardZoneRepository
from gildle.domain.entities.hazard_zone import HazardZone


class PgHazardZoneRepository(HazardZoneRepository):
    """HazardZoneRepository의 PostgreSQL 구현체(sync)."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def find_all(self) -> list[HazardZone]:
        session = self._session_factory()
        rows = session.execute(select(HazardZoneOrm)).scalars().all()
        return [HazardZone.from_orm(r) for r in rows]
