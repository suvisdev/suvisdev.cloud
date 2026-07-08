from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from gildle.adapter.outbound.orm.base import GildleBase


class TreeSegmentOrm(GildleBase):
    __tablename__ = "tree_segments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    road_name: Mapped[str | None] = mapped_column(nullable=True)
    start_latitude: Mapped[float]
    start_longitude: Mapped[float]
    end_latitude: Mapped[float]
    end_longitude: Mapped[float]
    species: Mapped[str]
    quantity: Mapped[int]
    managing_agency: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
