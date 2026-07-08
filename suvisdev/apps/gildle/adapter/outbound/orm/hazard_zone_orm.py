from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from gildle.adapter.outbound.orm.base import GildleBase


class HazardZoneOrm(GildleBase):
    __tablename__ = "hazard_zones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    center_latitude: Mapped[float]
    center_longitude: Mapped[float]
    radius_meters: Mapped[float]
    accident_count: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
