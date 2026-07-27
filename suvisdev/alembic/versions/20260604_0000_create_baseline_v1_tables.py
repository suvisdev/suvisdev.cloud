"""create baseline v1 tables (users/groups/admins, mova v1 schema, dispatch_adress, titanic_passengers, vision_uploads)

이 리비전 이전까지 이 테이블들은 alembic 체인에 없이 backend startup의
Base.metadata.create_all()로만 생성되어 왔다. 완전히 빈 DB에서
`alembic upgrade head`를 실행하면 뒤따르는 리비전들(20260701_0001,
41f584bfcb4e, 6d2f1b9a7c3e, f3a7c9e21b6d 등)이 여기서 만드는 테이블을
전제로 ALTER/FK를 걸기 때문에 "relation does not exist"로 실패했다.

각 테이블은 41f584bfcb4e 등 뒤따르는 리비전이 적용되기 직전 상태(v1
스키마)로 만든다 — 이후 리비전이 그 위에 그대로 적용되어야 최종
스키마가 현재 ORM과 일치한다.

Revision ID: 20260604_0000
Revises:
Create Date: 2026-07-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260604_0000"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- viewer: groups / admins / users ---
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_groups_code", "groups", ["code"])

    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("nickname", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_admins_group_id", "admins", ["group_id"])
    op.create_index("ix_admins_username", "admins", ["username"])
    op.create_index("ix_admins_email", "admins", ["email"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("nickname", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("gender", sa.String(length=16), nullable=False),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("preferred_genres", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("bio", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("age_group", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_group_id", "users", ["group_id"])
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_gender", "users", ["gender"])
    op.create_index("ix_users_age_group", "users", ["age_group"])

    # --- mova v1 schema (41f584bfcb4e가 이 위에 v2 스키마로 ALTER한다) ---
    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_collections_slug", "collections", ["slug"])

    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("release_year", sa.String(length=8), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False, server_default="0"),
        sa.Column("poster_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("platforms", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("age_rating", sa.String(length=8), nullable=True),
        sa.Column("genres", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_movies_slug", "movies", ["slug"])
    op.create_index("ix_movies_title", "movies", ["title"])
    op.create_index("ix_movies_age_rating", "movies", ["age_rating"])
    op.create_index("ix_movies_collection_id", "movies", ["collection_id"])

    op.create_table(
        "actors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("role_type", sa.String(length=16), nullable=False, server_default="actor"),
        sa.Column("profile_photo_url", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "role_type", name="uq_actors_name_role"),
    )
    op.create_index("ix_actors_name", "actors", ["name"])
    op.create_index("ix_actors_role_type", "actors", ["role_type"])

    op.create_table(
        "characters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["actors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("movie_id", "actor_id", name="uq_characters_movie_actor"),
    )
    op.create_index("ix_characters_movie_id", "characters", ["movie_id"])
    op.create_index("ix_characters_actor_id", "characters", ["actor_id"])

    op.create_table(
        "assistants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("default_model", sa.String(length=32), nullable=False, server_default="flash15"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_assistants_slug", "assistants", ["slug"])
    op.create_index("ix_assistants_is_active", "assistants", ["is_active"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=True),
        sa.Column("tag_kind", sa.String(length=16), nullable=False, server_default="mood"),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("movie_id", "slug", name="uq_tags_movie_slug"),
        sa.UniqueConstraint("character_id", name="uq_tags_character_id"),
    )
    op.create_index("ix_tags_movie_id", "tags", ["movie_id"])
    op.create_index("ix_tags_character_id", "tags", ["character_id"])
    op.create_index("ix_tags_tag_kind", "tags", ["tag_kind"])
    op.create_index("ix_tags_slug", "tags", ["slug"])

    op.create_table(
        "chat",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("assistant_id", sa.Integer(), nullable=True),
        sa.Column("raw_message", sa.Text(), nullable=False),
        sa.Column("refined_query", sa.String(length=255), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("intent_type", sa.String(length=32), nullable=False, server_default="mood"),
        sa.Column("search_filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "last_used_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assistant_id"], ["assistants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_user_id", "chat", ["user_id"])
    op.create_index("ix_chat_assistant_id", "chat", ["assistant_id"])
    op.create_index("ix_chat_refined_query", "chat", ["refined_query"])
    op.create_index("ix_chat_intent_type", "chat", ["intent_type"])

    op.create_table(
        "rankings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="box_office"),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("badge", sa.String(length=8), nullable=True),
        sa.Column("ranked_at", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chat_id"], ["chat.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rank", "ranked_at", "source", name="uq_rankings_rank_date_source"),
    )
    op.create_index("ix_rankings_rank", "rankings", ["rank"])
    op.create_index("ix_rankings_movie_id", "rankings", ["movie_id"])
    op.create_index("ix_rankings_chat_id", "rankings", ["chat_id"])
    op.create_index("ix_rankings_source", "rankings", ["source"])
    op.create_index("ix_rankings_ranked_at", "rankings", ["ranked_at"])

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column(
            "action_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reviews_user_id", "reviews", ["user_id"])
    op.create_index("ix_reviews_movie_id", "reviews", ["movie_id"])
    op.create_index("ix_reviews_action_type", "reviews", ["action_type"])
    op.create_index("ix_reviews_action_at", "reviews", ["action_at"])

    op.create_table(
        "picks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("pick_rank", sa.Integer(), nullable=False),
        sa.Column("hook", sa.String(length=120), nullable=True),
        sa.Column("title_snapshot", sa.String(length=255), nullable=False),
        sa.Column(
            "batch_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("feedback", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["chat_id"], ["chat.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_picks_chat_id", "picks", ["chat_id"])
    op.create_index("ix_picks_user_id", "picks", ["user_id"])
    op.create_index("ix_picks_movie_id", "picks", ["movie_id"])
    op.create_index("ix_picks_batch_at", "picks", ["batch_at"])
    op.create_index("ix_picks_feedback", "picks", ["feedback"])

    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column(
            "added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "movie_id", name="uq_watchlist_user_movie"),
    )
    op.create_index("ix_watchlist_user_id", "watchlist", ["user_id"])
    op.create_index("ix_watchlist_movie_id", "watchlist", ["movie_id"])

    # --- titanic: passengers (titanic_bookings의 FK 대상 — 6d2f1b9a7c3e가 여기로 FK를 건다) ---
    op.create_table(
        "titanic_passengers",
        sa.Column("passenger_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("gender", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("age", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("sib_sp", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("parch", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("survived", sa.String(length=8), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("passenger_id"),
    )
    op.create_index("ix_titanic_passengers_passenger_id", "titanic_passengers", ["passenger_id"])

    # --- dispatch: 주소록 (20260701_0001이 이 위에 email UNIQUE 제약을 건다) ---
    op.create_table(
        "dispatch_adress",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("middle_name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("last_name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("phonetic_first_name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("phonetic_middle_name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("phonetic_last_name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("name_prefix", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("name_suffix", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("nickname", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("file_as", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("organization_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("organization_title", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("organization_department", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("birthday", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("photo", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("labels", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("email_label", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- ontology: 비전 업로드 원본 ---
    op.create_table(
        "vision_uploads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("vision_uploads")
    op.drop_table("dispatch_adress")

    op.drop_index("ix_titanic_passengers_passenger_id", table_name="titanic_passengers")
    op.drop_table("titanic_passengers")

    op.drop_index("ix_watchlist_movie_id", table_name="watchlist")
    op.drop_index("ix_watchlist_user_id", table_name="watchlist")
    op.drop_table("watchlist")

    op.drop_index("ix_picks_feedback", table_name="picks")
    op.drop_index("ix_picks_batch_at", table_name="picks")
    op.drop_index("ix_picks_movie_id", table_name="picks")
    op.drop_index("ix_picks_user_id", table_name="picks")
    op.drop_index("ix_picks_chat_id", table_name="picks")
    op.drop_table("picks")

    op.drop_index("ix_reviews_action_at", table_name="reviews")
    op.drop_index("ix_reviews_action_type", table_name="reviews")
    op.drop_index("ix_reviews_movie_id", table_name="reviews")
    op.drop_index("ix_reviews_user_id", table_name="reviews")
    op.drop_table("reviews")

    op.drop_index("ix_rankings_ranked_at", table_name="rankings")
    op.drop_index("ix_rankings_source", table_name="rankings")
    op.drop_index("ix_rankings_chat_id", table_name="rankings")
    op.drop_index("ix_rankings_movie_id", table_name="rankings")
    op.drop_index("ix_rankings_rank", table_name="rankings")
    op.drop_table("rankings")

    op.drop_index("ix_chat_intent_type", table_name="chat")
    op.drop_index("ix_chat_refined_query", table_name="chat")
    op.drop_index("ix_chat_assistant_id", table_name="chat")
    op.drop_index("ix_chat_user_id", table_name="chat")
    op.drop_table("chat")

    op.drop_index("ix_tags_slug", table_name="tags")
    op.drop_index("ix_tags_tag_kind", table_name="tags")
    op.drop_index("ix_tags_character_id", table_name="tags")
    op.drop_index("ix_tags_movie_id", table_name="tags")
    op.drop_table("tags")

    op.drop_index("ix_assistants_is_active", table_name="assistants")
    op.drop_index("ix_assistants_slug", table_name="assistants")
    op.drop_table("assistants")

    op.drop_index("ix_characters_actor_id", table_name="characters")
    op.drop_index("ix_characters_movie_id", table_name="characters")
    op.drop_table("characters")

    op.drop_index("ix_actors_role_type", table_name="actors")
    op.drop_index("ix_actors_name", table_name="actors")
    op.drop_table("actors")

    op.drop_index("ix_movies_collection_id", table_name="movies")
    op.drop_index("ix_movies_age_rating", table_name="movies")
    op.drop_index("ix_movies_title", table_name="movies")
    op.drop_index("ix_movies_slug", table_name="movies")
    op.drop_table("movies")

    op.drop_index("ix_collections_slug", table_name="collections")
    op.drop_table("collections")

    op.drop_index("ix_users_age_group", table_name="users")
    op.drop_index("ix_users_gender", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_group_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_admins_email", table_name="admins")
    op.drop_index("ix_admins_username", table_name="admins")
    op.drop_index("ix_admins_group_id", table_name="admins")
    op.drop_table("admins")

    op.drop_index("ix_groups_code", table_name="groups")
    op.drop_table("groups")
