"""create gildle tables

Revision ID: 0b92552ee0d7
Revises: 20260604_0001
Create Date: 2026-06-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0b92552ee0d7"
down_revision: str | None = "20260604_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hazard_zones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("center_latitude", sa.Float(), nullable=False),
        sa.Column("center_longitude", sa.Float(), nullable=False),
        sa.Column("radius_meters", sa.Float(), nullable=False),
        sa.Column("accident_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "route_nodes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("node_type", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "route_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("start_latitude", sa.Float(), nullable=False),
        sa.Column("start_longitude", sa.Float(), nullable=False),
        sa.Column("end_latitude", sa.Float(), nullable=False),
        sa.Column("end_longitude", sa.Float(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tree_segments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("road_name", sa.String(), nullable=True),
        sa.Column("start_latitude", sa.Float(), nullable=False),
        sa.Column("start_longitude", sa.Float(), nullable=False),
        sa.Column("end_latitude", sa.Float(), nullable=False),
        sa.Column("end_longitude", sa.Float(), nullable=False),
        sa.Column("species", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("managing_agency", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # route_edges: from_node_id / to_node_id 둘 다 route_nodes.id를 거는 self-ref FK.
    op.create_table(
        "route_edges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("from_node_id", sa.Integer(), nullable=False),
        sa.Column("to_node_id", sa.Integer(), nullable=False),
        sa.Column("base_distance_m", sa.Float(), nullable=False),
        sa.Column("road_name", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["from_node_id"], ["route_nodes.id"]),
        sa.ForeignKeyConstraint(["to_node_id"], ["route_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_route_edges_from_node_id"), "route_edges", ["from_node_id"], unique=False
    )
    op.create_index(
        op.f("ix_route_edges_to_node_id"), "route_edges", ["to_node_id"], unique=False
    )
    # route_results: route_requests와 1:1 — route_request_id에 UNIQUE 제약.
    op.create_table(
        "route_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("route_request_id", sa.Integer(), nullable=False),
        sa.Column("path_node_ids", sa.JSON(), nullable=False),
        sa.Column("total_weight", sa.Float(), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["route_request_id"], ["route_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "route_request_id", name="uq_route_results_route_request_id"
        ),
    )


def downgrade() -> None:
    op.drop_table("route_results")
    op.drop_index(op.f("ix_route_edges_to_node_id"), table_name="route_edges")
    op.drop_index(op.f("ix_route_edges_from_node_id"), table_name="route_edges")
    op.drop_table("route_edges")
    op.drop_table("tree_segments")
    op.drop_table("route_requests")
    op.drop_table("route_nodes")
    op.drop_table("hazard_zones")
