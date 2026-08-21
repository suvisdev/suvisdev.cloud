from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gildle.adapter.outbound.orm.base import GildleBase
from gildle.adapter.outbound.orm.route_node_orm import RouteNodeOrm


class RouteEdgeOrm(GildleBase):
    __tablename__ = "route_edges"
    __table_args__ = (
        CheckConstraint("tree_score >= 0 AND tree_score <= 1", name="ck_tree_score_range"),
        CheckConstraint("hazard_score >= 0 AND hazard_score <= 1", name="ck_hazard_score_range"),
        CheckConstraint(
            "dog_friendly_score >= 0 AND dog_friendly_score <= 1",
            name="ck_dog_friendly_score_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    from_node_id: Mapped[int] = mapped_column(
        ForeignKey("route_nodes.id"), nullable=False, index=True
    )
    to_node_id: Mapped[int] = mapped_column(
        ForeignKey("route_nodes.id"), nullable=False, index=True
    )
    base_distance_m: Mapped[float]
    road_name: Mapped[str | None] = mapped_column(nullable=True)
    tree_score: Mapped[float] = mapped_column(default=0.0, server_default="0")
    hazard_score: Mapped[float] = mapped_column(default=0.0, server_default="0")
    dog_friendly_score: Mapped[float] = mapped_column(default=0.0, server_default="0")

    from_node: Mapped[RouteNodeOrm] = relationship(foreign_keys=[from_node_id])
    to_node: Mapped[RouteNodeOrm] = relationship(foreign_keys=[to_node_id])
