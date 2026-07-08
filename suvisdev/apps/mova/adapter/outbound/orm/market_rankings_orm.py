"""@see suvisdev/_claude/ENTITY_RULE.md — Mova HOT 랭킹 (영화·chat FK)."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel
from mova.domain.value_objects.market_rankings_vo import RANKING_SOURCE_BOX_OFFICE


class MovaRanking(MovaModel):
    """HOT ��ŷ ������. `source`�� �Ϻ� TOP N ? chat_trend�� picks��chat ����."""

    __tablename__ = "rankings"
    __table_args__ = (
        UniqueConstraint("rank", "ranked_at", "source", name="uq_rankings_rank_date_source"),
    )

    rank: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    movie_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chat_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("chat.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="source=chat_trend ? ��ǥ �˻� �ǵ� chat.id",
    )
    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=RANKING_SOURCE_BOX_OFFICE,
        index=True,
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    badge: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ranked_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
