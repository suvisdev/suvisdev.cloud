"""create kleague tables

Revision ID: c529c3d9c385
Revises: 20260702_0003
Create Date: 2026-07-13 06:03:27.739548

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c529c3d9c385"
down_revision: str | None = "20260702_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stadium",
        sa.Column("stadium_id", sa.String(length=10), nullable=False),
        sa.Column("stadium_name", sa.String(length=40), nullable=True),
        sa.Column("hometeam_id", sa.String(length=10), nullable=True),
        sa.Column("seat_count", sa.Integer(), nullable=True),
        sa.Column("address", sa.String(length=60), nullable=True),
        sa.Column("ddd", sa.String(length=10), nullable=True),
        sa.Column("tel", sa.String(length=10), nullable=True),
        sa.PrimaryKeyConstraint("stadium_id"),
    )
    op.create_table(
        "schedule",
        sa.Column("sche_date", sa.String(length=10), nullable=False),
        sa.Column("stadium_id", sa.String(length=10), nullable=False),
        sa.Column("gubun", sa.String(length=10), nullable=True),
        sa.Column("hometeam_id", sa.String(length=10), nullable=True),
        sa.Column("awayteam_id", sa.String(length=10), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["stadium_id"], ["stadium.stadium_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("sche_date", "stadium_id"),
    )
    op.create_table(
        "team",
        sa.Column("team_id", sa.String(length=10), nullable=False),
        sa.Column("region_name", sa.String(length=10), nullable=True),
        sa.Column("team_name", sa.String(length=40), nullable=True),
        sa.Column("e_team_name", sa.String(length=50), nullable=True),
        sa.Column("orig_yyyy", sa.String(length=10), nullable=True),
        sa.Column("zip_code1", sa.String(length=10), nullable=True),
        sa.Column("zip_code2", sa.String(length=10), nullable=True),
        sa.Column("address", sa.String(length=80), nullable=True),
        sa.Column("ddd", sa.String(length=10), nullable=True),
        sa.Column("tel", sa.String(length=10), nullable=True),
        sa.Column("fax", sa.String(length=10), nullable=True),
        sa.Column("homepage", sa.String(length=50), nullable=True),
        sa.Column("owner", sa.String(length=10), nullable=True),
        sa.Column("stadium_id", sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(["stadium_id"], ["stadium.stadium_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("team_id"),
    )
    op.create_table(
        "player",
        sa.Column("player_id", sa.String(length=10), nullable=False),
        sa.Column("player_name", sa.String(length=20), nullable=True),
        sa.Column("e_player_name", sa.String(length=40), nullable=True),
        sa.Column("nickname", sa.String(length=30), nullable=True),
        sa.Column("join_yyyy", sa.String(length=10), nullable=True),
        sa.Column("position", sa.String(length=10), nullable=True),
        sa.Column("back_no", sa.Integer(), nullable=True),
        sa.Column("nation", sa.String(length=20), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("solar", sa.String(length=10), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=True),
        sa.Column("team_id", sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["team.team_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("player_id"),
    )


def downgrade() -> None:
    op.drop_table("player")
    op.drop_table("team")
    op.drop_table("schedule")
    op.drop_table("stadium")
