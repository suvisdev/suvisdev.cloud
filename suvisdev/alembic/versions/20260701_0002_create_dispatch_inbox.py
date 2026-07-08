"""create dispatch_inbox table

Revision ID: 20260701_0002
Revises: 20260701_0001
Create Date: 2026-07-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0002"
down_revision: str | None = "20260701_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dispatch_inbox",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sender", sa.Text, nullable=False, server_default=""),
        sa.Column("subject", sa.Text, nullable=False, server_default=""),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("received_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("dispatch_inbox")
