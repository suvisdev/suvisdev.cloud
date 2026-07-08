"""@see suvisdev/_claude/ENTITY_RULE.md — Mova AI 채팅 검색·취향 의도 로그."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel
from viewer.adapter.outbound.orm.user_orm import User


class MovaChat(MovaModel):
    """Mova 채팅방 사용자 검색·의도 로그. PK `id`."""

    __tablename__ = "chat"

    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(User.__table__.c.id, ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Viewer users.id (동일 DB FK, 비로그인은 NULL)",
    )
    assistant_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("assistants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="담당 AI assistants.id",
    )
    raw_message: Mapped[str] = mapped_column(Text, nullable=False)
    refined_query: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    intent_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="mood",
        index=True,
        comment="filter_and | similar_person | mood",
    )
    search_filters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="must(AND) / similar_to 등 분류·검색용",
    )
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
