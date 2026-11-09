from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from deolmi.adapter.outbound.orm.base import DeolmiBase


class DeolmiEventOrm(DeolmiBase):
    """/score 한 번에 한 줄. 입력 글자는 없다 — 리듬·궤적 수치(signals)와 판정만."""

    __tablename__ = "deolmi_events"
    __table_args__ = (Index("ix_deolmi_events_site_id_created_at", "site_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("deolmi_sites.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    ip: Mapped[str | None]
    score: Mapped[float]
    verdict: Mapped[str]
    rule_score: Mapped[float]
    model_score: Mapped[float | None]
    decided_by: Mapped[str]
    signals: Mapped[dict[str, Any]] = mapped_column(JSONB)
    reasons: Mapped[list[str]] = mapped_column(JSONB)
