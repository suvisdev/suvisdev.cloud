from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_neo_theone_base import Base


class VisitorActivityOrm(Base):
    """익명 방문자 일별 방문 기록. visitor_id는 클라이언트가 만든 쿠키 UUID — PII 없음."""

    __tablename__ = "visitor_activity"
    __table_args__ = (
        Index("ix_visitor_activity_last_seen_at", "last_seen_at"),
        Index("ix_visitor_activity_visit_date", "visit_date"),
    )

    visitor_id: Mapped[str] = mapped_column(primary_key=True)
    visit_date: Mapped[date] = mapped_column(Date, primary_key=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # 2026-09-29: 09-28 방문 22명 중 19명이 새 쿠키·0초 체류 — 사람·봇을 못 가르던 것. 첫 핑의
    # User-Agent로 판정하고(규칙은 record_visit_interactor), UA 원문은 사후 확인용으로 앞 256자만.
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)
