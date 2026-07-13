from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from contents.adapter.outbound.orm.base import ContentsBase


class PlayerOrm(ContentsBase):
    """K-리그 선수."""

    __tablename__ = "player"

    player_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    player_name: Mapped[str | None] = mapped_column(String(20), nullable=True)
    e_player_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(30), nullable=True)
    join_yyyy: Mapped[str | None] = mapped_column(String(10), nullable=True)
    position: Mapped[str | None] = mapped_column(String(10), nullable=True)
    back_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    solar: Mapped[str | None] = mapped_column(String(10), nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("team.team_id", ondelete="RESTRICT"), nullable=False
    )
