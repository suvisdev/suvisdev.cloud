"""mova v2 schema

Revision ID: 41f584bfcb4e
Revises: c529c3d9c385
Create Date: 2026-07-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "41f584bfcb4e"
down_revision: str | None = "c529c3d9c385"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_actions",
        sa.Column(
            "user_id", sa.Integer(), nullable=False, comment="Viewer users.id (동일 DB FK)"
        ),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column(
            "action_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_actions_action_at"), "user_actions", ["action_at"], unique=False
    )
    op.create_index(
        op.f("ix_user_actions_action_type"), "user_actions", ["action_type"], unique=False
    )
    op.create_index(
        op.f("ix_user_actions_movie_id"), "user_actions", ["movie_id"], unique=False
    )
    op.create_index(
        op.f("ix_user_actions_user_id"), "user_actions", ["user_id"], unique=False
    )
    op.add_column(
        "actors",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.add_column(
        "actors",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.add_column(
        "assistants",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.add_column(
        "assistants",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.add_column("characters", sa.Column("character_name", sa.String(length=50), nullable=False))
    op.add_column(
        "characters",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.add_column(
        "characters",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.drop_constraint(op.f("uq_characters_movie_actor"), "characters", type_="unique")
    op.create_unique_constraint(
        "uq_characters_movie_actor_name", "characters", ["movie_id", "actor_id", "character_name"]
    )
    op.add_column(
        "collections",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.add_column(
        "collections",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.add_column(
        "movies",
        sa.Column(
            "embedding",
            Vector(768),
            nullable=True,
            comment="추천용 임베딩. HNSW/IVFFlat 인덱스는 별도 리비전",
        ),
    )
    op.add_column(
        "movies",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.add_column(
        "movies",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.alter_column(
        "movies",
        "release_year",
        existing_type=sa.VARCHAR(length=8),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="release_year::integer",
    )
    op.drop_column("movies", "genres")
    op.alter_column(
        "rankings",
        "chat_id",
        existing_type=sa.INTEGER(),
        comment="source=chat_trend일 때 근거가 된 chat.id",
        existing_comment="source=chat_trend ? 근거 검색 의도 chat.id",
        existing_nullable=True,
    )
    op.add_column(
        "reviews",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.drop_index(op.f("ix_reviews_action_at"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_action_type"), table_name="reviews")
    op.create_unique_constraint("uq_reviews_user_movie", "reviews", ["user_id", "movie_id"])
    op.drop_column("reviews", "action_type")
    op.drop_column("reviews", "action_at")
    op.add_column(
        "tags",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.add_column(
        "tags",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    op.alter_column("tags", "movie_id", existing_type=sa.INTEGER(), nullable=True)
    op.alter_column(
        "tags",
        "character_id",
        existing_type=sa.INTEGER(),
        comment="cast 태그일 때 characters.id (영화-인물 유도)",
        existing_comment="cast 태그일 때 characters.id (영화·인물 유도)",
        existing_nullable=True,
    )
    op.drop_index(op.f("ix_users_age_group"), table_name="users")
    op.drop_column("users", "age_group")


def downgrade() -> None:
    op.add_column(
        "users", sa.Column("age_group", sa.VARCHAR(length=16), autoincrement=False, nullable=False)
    )
    op.create_index(op.f("ix_users_age_group"), "users", ["age_group"], unique=False)
    op.alter_column(
        "tags",
        "character_id",
        existing_type=sa.INTEGER(),
        comment="cast 태그일 때 characters.id (영화·인물 유도)",
        existing_comment="cast 태그일 때 characters.id (영화-인물 유도)",
        existing_nullable=True,
    )
    op.alter_column("tags", "movie_id", existing_type=sa.INTEGER(), nullable=False)
    op.drop_column("tags", "updated_at")
    op.drop_column("tags", "created_at")
    op.add_column(
        "reviews",
        sa.Column(
            "action_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "reviews", sa.Column("action_type", sa.VARCHAR(length=32), autoincrement=False, nullable=False)
    )
    op.drop_constraint("uq_reviews_user_movie", "reviews", type_="unique")
    op.create_index(op.f("ix_reviews_action_type"), "reviews", ["action_type"], unique=False)
    op.create_index(op.f("ix_reviews_action_at"), "reviews", ["action_at"], unique=False)
    op.drop_column("reviews", "updated_at")
    op.drop_column("reviews", "created_at")
    op.alter_column(
        "rankings",
        "chat_id",
        existing_type=sa.INTEGER(),
        comment="source=chat_trend ? 근거 검색 의도 chat.id",
        existing_comment="source=chat_trend일 때 근거가 된 chat.id",
        existing_nullable=True,
    )
    op.add_column(
        "movies",
        sa.Column(
            "genres", postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False
        ),
    )
    op.alter_column(
        "movies",
        "release_year",
        existing_type=sa.Integer(),
        type_=sa.VARCHAR(length=8),
        existing_nullable=False,
    )
    op.drop_column("movies", "updated_at")
    op.drop_column("movies", "created_at")
    op.drop_column("movies", "embedding")
    op.drop_column("collections", "updated_at")
    op.drop_column("collections", "created_at")
    op.drop_constraint("uq_characters_movie_actor_name", "characters", type_="unique")
    op.create_unique_constraint(
        op.f("uq_characters_movie_actor"), "characters", ["movie_id", "actor_id"]
    )
    op.drop_column("characters", "updated_at")
    op.drop_column("characters", "created_at")
    op.drop_column("characters", "character_name")
    op.drop_column("assistants", "updated_at")
    op.drop_column("assistants", "created_at")
    op.drop_column("actors", "updated_at")
    op.drop_column("actors", "created_at")
    op.drop_index(op.f("ix_user_actions_user_id"), table_name="user_actions")
    op.drop_index(op.f("ix_user_actions_movie_id"), table_name="user_actions")
    op.drop_index(op.f("ix_user_actions_action_type"), table_name="user_actions")
    op.drop_index(op.f("ix_user_actions_action_at"), table_name="user_actions")
    op.drop_table("user_actions")
