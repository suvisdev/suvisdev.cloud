"""drop legacy titanic_persons, fix titanic_bookings FK to titanic_passengers

titanic_persons/titanic_bookings(person_id FK, Integer)는 20260604_0001에서 만들어졌으나
이후 ORM이 titanic_passengers/titanic_bookings(passenger_id FK, String)로 바뀌면서
create_all()이 titanic_passengers만 새로 만들고 titanic_bookings는 옛 컬럼 그대로 남았다.
즉 실제 DB의 titanic_bookings는 현재 ORM(RoseModelOrm)과 컬럼부터 다른 상태였다.
양쪽 다 0 rows 확인 후 정리.

Revision ID: 6d2f1b9a7c3e
Revises: 41f584bfcb4e
Create Date: 2026-07-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6d2f1b9a7c3e"
down_revision: str | None = "41f584bfcb4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("titanic_bookings_person_id_fkey", "titanic_bookings", type_="foreignkey")
    op.drop_index("ix_titanic_bookings_person_id", table_name="titanic_bookings")
    op.drop_column("titanic_bookings", "person_id")

    op.drop_index("ix_titanic_persons_passenger_id", table_name="titanic_persons")
    op.drop_table("titanic_persons")

    op.add_column(
        "titanic_bookings",
        sa.Column("passenger_id", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_titanic_bookings_passenger_id", "titanic_bookings", ["passenger_id"])
    op.create_foreign_key(
        "titanic_bookings_passenger_id_fkey",
        "titanic_bookings",
        "titanic_passengers",
        ["passenger_id"],
        ["passenger_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("titanic_bookings_passenger_id_fkey", "titanic_bookings", type_="foreignkey")
    op.drop_index("ix_titanic_bookings_passenger_id", table_name="titanic_bookings")
    op.drop_column("titanic_bookings", "passenger_id")

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

    op.add_column(
        "titanic_bookings",
        sa.Column("person_id", sa.Integer(), nullable=False),
    )
    op.create_index("ix_titanic_bookings_person_id", "titanic_bookings", ["person_id"])
    op.create_foreign_key(
        "titanic_bookings_person_id_fkey",
        "titanic_bookings",
        "titanic_persons",
        ["person_id"],
        ["id"],
    )
