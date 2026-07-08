from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from gildle.adapter.outbound.orm.base import GildleBase


class RouteRequestOrm(GildleBase):
    __tablename__ = "route_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    start_latitude: Mapped[float]
    start_longitude: Mapped[float]
    end_latitude: Mapped[float]
    end_longitude: Mapped[float]
    mode: Mapped[str]
    requested_at: Mapped[datetime] = mapped_column(server_default=func.now())
