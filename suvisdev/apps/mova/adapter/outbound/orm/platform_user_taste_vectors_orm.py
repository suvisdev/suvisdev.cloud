"""@see suvisdev/_claude/ENTITY_RULE.md — 유저 취향 벡터(리뷰 임베딩 별점 가중 평균)."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel
from viewer.adapter.outbound.orm.user_orm import User

_EMBEDDING_DIM = 768


class MovaUserTasteVector(MovaModel):
    """유저당 1행. 본인 리뷰 임베딩의 별점 가중 평균 — 개인화 추천 신호.

    갱신 트리거: 리뷰 임베딩 저장 성공 후 BackgroundTasks가 재계산(주 경로) +
    매일 KST 03:45 크론 안전망. `review_count`가 0이면(리뷰가 다 삭제되면)
    행 자체를 삭제하지 않고 vector=NULL 상태 그대로 둔다 —
    upsert-vs-delete 결정을 단순화한다.
    """

    __tablename__ = "user_taste_vectors"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_taste_vectors_user_id"),)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(User.__table__.c.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Viewer users.id (동일 DB FK)",
    )
    vector: Mapped[list[float] | None] = mapped_column(
        Vector(_EMBEDDING_DIM),
        nullable=True,
        comment="본인 리뷰 임베딩의 별점 가중 평균. 리뷰 0건이면 NULL",
    )
    review_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="가중 평균에 포함된 리뷰 수(embedding IS NOT NULL AND rating IS NOT NULL)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
