"""create titanic_persons and titanic_bookings

Revision ID: 20260604_0001
Revises:
Create Date: 2026-06-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260604_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "titanic_persons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("passenger_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("gender", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("age", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("sib_sp", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("parch", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("survived", sa.String(length=8), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("passenger_id"),
    )
    op.create_index("ix_titanic_persons_passenger_id", "titanic_persons", ["passenger_id"])

    op.create_table(
        "titanic_bookings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("pclass", sa.String(length=8), nullable=False, server_default=""),
        sa.Column("ticket", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("fare", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("cabin", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("embarked", sa.String(length=8), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["person_id"], ["titanic_persons.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_titanic_bookings_person_id", "titanic_bookings", ["person_id"])


def downgrade() -> None:
    op.drop_index("ix_titanic_bookings_person_id", table_name="titanic_bookings")
    op.drop_table("titanic_bookings")
    op.drop_index("ix_titanic_persons_passenger_id", table_name="titanic_persons")
    op.drop_table("titanic_persons")
