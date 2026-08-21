"""gildle: route_edges에 score 3컬럼 + route_nodes에 osm_id 추가

Revision ID: 20260821_0001
Revises: 20260813_0001
Create Date: 2026-08-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260821_0001"
down_revision: str | None = "20260813_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "route_nodes",
        sa.Column("osm_id", sa.String(), nullable=True),
    )
    op.create_unique_constraint("uq_route_nodes_osm_id", "route_nodes", ["osm_id"])

    op.add_column(
        "route_edges",
        sa.Column("tree_score", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "route_edges",
        sa.Column("hazard_score", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "route_edges",
        sa.Column("dog_friendly_score", sa.Float(), server_default="0", nullable=False),
    )

    op.create_check_constraint(
        "ck_tree_score_range", "route_edges", "tree_score >= 0 AND tree_score <= 1"
    )
    op.create_check_constraint(
        "ck_hazard_score_range", "route_edges", "hazard_score >= 0 AND hazard_score <= 1"
    )
    op.create_check_constraint(
        "ck_dog_friendly_score_range",
        "route_edges",
        "dog_friendly_score >= 0 AND dog_friendly_score <= 1",
    )


def downgrade() -> None:
    op.drop_constraint("ck_dog_friendly_score_range", "route_edges", type_="check")
    op.drop_constraint("ck_hazard_score_range", "route_edges", type_="check")
    op.drop_constraint("ck_tree_score_range", "route_edges", type_="check")

    op.drop_column("route_edges", "dog_friendly_score")
    op.drop_column("route_edges", "hazard_score")
    op.drop_column("route_edges", "tree_score")

    op.drop_constraint("uq_route_nodes_osm_id", "route_nodes", type_="unique")
    op.drop_column("route_nodes", "osm_id")
