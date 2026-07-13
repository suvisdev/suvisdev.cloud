from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from contents.adapter.outbound.orm.base import ContentsBase


class ScheduleOrm(ContentsBase):
    """K-리그 경기 일정. 복합 PK: (sche_date, stadium_id)."""

    __tablename__ = "schedule"

    sche_date: Mapped[str] = mapped_column(String(10), primary_key=True)
    stadium_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stadium.stadium_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    gubun: Mapped[str | None] = mapped_column(String(10), nullable=True)
    hometeam_id: Mapped[str | None] = mapped_column(String(10), nullable=True)
    awayteam_id: Mapped[str | None] = mapped_column(String(10), nullable=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
