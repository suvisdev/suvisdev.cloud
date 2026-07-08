from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gildle.adapter.outbound.orm.base import GildleBase
from gildle.adapter.outbound.orm.route_request_orm import RouteRequestOrm


class RouteResultOrm(GildleBase):
    __tablename__ = "route_results"

    # route_requests와 1:1 — UNIQUE 제약으로 한 요청당 결과 하나를 보장한다.
    __table_args__ = (
        UniqueConstraint(
            "route_request_id", name="uq_route_results_route_request_id"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route_request_id: Mapped[int] = mapped_column(
        ForeignKey("route_requests.id"), nullable=False
    )
    path_node_ids: Mapped[list[Any]] = mapped_column(JSON)
    total_weight: Mapped[float]
    calculated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    request: Mapped[RouteRequestOrm] = relationship()
