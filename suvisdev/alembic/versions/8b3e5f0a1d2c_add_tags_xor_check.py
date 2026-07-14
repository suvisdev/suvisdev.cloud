"""add tags XOR check constraint (missed by autogenerate)

studio_tags_orm.py는 ck_tags_exactly_one_target CheckConstraint를 이미 정의하고
있었지만, alembic autogenerate가 기본적으로 CheckConstraint 변경은 감지하지
않아 41f584bfcb4e에 포함되지 못했다. tags 0 rows 확인 후 수동으로 추가.

Revision ID: 8b3e5f0a1d2c
Revises: 6d2f1b9a7c3e
Create Date: 2026-07-14

"""

from collections.abc import Sequence

from alembic import op

revision: str = "8b3e5f0a1d2c"
down_revision: str | None = "6d2f1b9a7c3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_tags_exactly_one_target",
        "tags",
        "(character_id IS NULL) != (movie_id IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tags_exactly_one_target", "tags", type_="check")
