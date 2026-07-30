"""add TMDB credits backfill support (actors.tmdb_person_id, characters.billing_order, movie_directors)

TMDB credits(cast/crew) 백필을 위한 스키마 확장. actors/characters는 지금까지
쓰기 경로가 전혀 없어 0행이었다(_docs/WORK_LOG.md 2026-07-30 조사 참고) — 그
사실을 이용해 아래 4건을 한 리비전으로 묶는다.

1. actors.tmdb_person_id — upsert 키. 이름만으로는 동명이인을 구분 못 해
   TMDB person id를 외부 식별자로 둔다.
2. characters.billing_order — TMDB credits.cast[].order(주연/조연 순서) 저장.
3. movie_directors(movie_id, actor_id) — 영화-감독 관계. characters와 대칭
   구조(1인 다역처럼 공동 감독 지원), character_name이 필요 없어 별도 테이블로
   분리. actors.role_type='director'로 배우/감독을 이미 구분하므로 이 테이블은
   "어느 영화를 누가 감독했는지"만 담는다.
4. uq_actors_name_role DROP — tmdb_person_id UNIQUE가 그 역할을 대체한다.
   동명이인(다른 tmdb_person_id, 같은 name+role_type)의 두 번째 upsert가 이
   제약에 막히므로 반드시 함께 드롭해야 한다. actors가 0행인 지금이 무손실로
   드롭할 수 있는 유일한 시점(데이터가 들어온 뒤엔 제약 위반 없이 못 드롭한다).

Revision ID: 20260730_0001
Revises: 20260729_0002
Create Date: 2026-07-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0001"
down_revision: str | None = "20260729_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_actors_name_role", "actors", type_="unique")
    op.add_column(
        "actors",
        sa.Column("tmdb_person_id", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint("uq_actors_tmdb_person_id", "actors", ["tmdb_person_id"])
    op.create_index("ix_actors_tmdb_person_id", "actors", ["tmdb_person_id"])

    op.add_column(
        "characters",
        sa.Column("billing_order", sa.Integer(), nullable=True),
    )

    op.create_table(
        "movie_directors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["actors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("movie_id", "actor_id", name="uq_movie_directors_movie_actor"),
    )
    op.create_index("ix_movie_directors_movie_id", "movie_directors", ["movie_id"])
    op.create_index("ix_movie_directors_actor_id", "movie_directors", ["actor_id"])


def downgrade() -> None:
    op.drop_index("ix_movie_directors_actor_id", table_name="movie_directors")
    op.drop_index("ix_movie_directors_movie_id", table_name="movie_directors")
    op.drop_table("movie_directors")

    op.drop_column("characters", "billing_order")

    op.drop_index("ix_actors_tmdb_person_id", table_name="actors")
    op.drop_constraint("uq_actors_tmdb_person_id", "actors", type_="unique")
    op.drop_column("actors", "tmdb_person_id")
    op.create_unique_constraint("uq_actors_name_role", "actors", ["name", "role_type"])
