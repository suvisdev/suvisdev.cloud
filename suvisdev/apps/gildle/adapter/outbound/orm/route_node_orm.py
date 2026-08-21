from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from gildle.adapter.outbound.orm.base import GildleBase


class RouteNodeOrm(GildleBase):
    __tablename__ = "route_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    latitude: Mapped[float]
    longitude: Mapped[float]
    node_type: Mapped[str]
    osm_id: Mapped[str | None] = mapped_column(nullable=True, unique=True)
