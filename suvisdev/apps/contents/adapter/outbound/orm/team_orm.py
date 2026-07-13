from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from contents.adapter.outbound.orm.base import ContentsBase


class TeamOrm(ContentsBase):
    """K-리그 구단."""

    __tablename__ = "team"

    team_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    region_name: Mapped[str | None] = mapped_column(String(10), nullable=True)
    team_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    e_team_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    orig_yyyy: Mapped[str | None] = mapped_column(String(10), nullable=True)
    zip_code1: Mapped[str | None] = mapped_column(String(10), nullable=True)
    zip_code2: Mapped[str | None] = mapped_column(String(10), nullable=True)
    address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ddd: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tel: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fax: Mapped[str | None] = mapped_column(String(10), nullable=True)
    homepage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(10), nullable=True)
    stadium_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("stadium.stadium_id", ondelete="RESTRICT"), nullable=False
    )
