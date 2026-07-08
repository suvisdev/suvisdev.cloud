from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gildle.adapter.outbound.orm.base import GildleBase
from gildle.adapter.outbound.orm.route_node_orm import RouteNodeOrm


class RouteEdgeOrm(GildleBase):
    __tablename__ = "route_edges"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # from_node_id / to_node_id 둘 다 route_nodes.id를 가리키는 self-ref FK다.
    from_node_id: Mapped[int] = mapped_column(
        ForeignKey("route_nodes.id"), nullable=False, index=True
    )
    to_node_id: Mapped[int] = mapped_column(
        ForeignKey("route_nodes.id"), nullable=False, index=True
    )
    base_distance_m: Mapped[float]
    road_name: Mapped[str | None] = mapped_column(nullable=True)

    # 동일 테이블을 두 번 참조하므로 foreign_keys로 모호성을 해소한다.
    from_node: Mapped[RouteNodeOrm] = relationship(foreign_keys=[from_node_id])
    to_node: Mapped[RouteNodeOrm] = relationship(foreign_keys=[to_node_id])
