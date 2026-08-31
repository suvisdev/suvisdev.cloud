"""@see suvisdev/_claude/ENTITY_RULE.md — 사용자↔영화 별점·감상평 리뷰(단일 테이블 `reviews`)."""

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel
from viewer.adapter.outbound.orm.user_orm import User

_EMBEDDING_DIM = 768


class MovaReview(MovaModel):
    """사용자↔영화 별점·감상평. PK `id` — user+movie당 리뷰 1건 (수정은 UPDATE)."""

    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_reviews_user_movie"),)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(User.__table__.c.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Viewer users.id (동일 DB FK)",
    )
    movie_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(_EMBEDDING_DIM),
        nullable=True,
        comment="body 임베딩. body=NULL이면 컬럼도 NULL. HNSW 인덱스 idx_reviews_embedding_hnsw",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    sentiment_label: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Echo 감정분석 결과 라벨 (긍정/부정). body=NULL이면 NULL.",
    )
    sentiment_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Echo 감정분석 신뢰도 (0~1). body=NULL이면 NULL.",
    )
    news_source_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="에디터 리뷰 생성 시 참고한 뉴스 기사 수. 일반 유저 리뷰는 NULL.",
    )
    spoiler_spans: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        comment=(
            "AI가 판단한 스포일러 문구 스팬 리스트. 각 항목은 "
            "{start:int, end:int, text:str}. body 문자열 인덱스(파이썬 슬라이스 규칙)."
        ),
    )
