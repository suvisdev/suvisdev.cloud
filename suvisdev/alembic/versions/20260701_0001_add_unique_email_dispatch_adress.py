"""add unique constraint to dispatch_adress.email

Revision ID: 20260701_0001
Revises: 0b92552ee0d7
Create Date: 2026-07-01

"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260701_0001"
down_revision: str | None = "0b92552ee0d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        DELETE FROM dispatch_adress
        WHERE id NOT IN (
            SELECT MIN(id) FROM dispatch_adress GROUP BY email
        )
    """)
    op.create_unique_constraint("uq_dispatch_adress_email", "dispatch_adress", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_dispatch_adress_email", "dispatch_adress", type_="unique")
