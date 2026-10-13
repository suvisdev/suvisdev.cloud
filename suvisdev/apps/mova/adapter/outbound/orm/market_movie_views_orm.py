"""영화 상세 열람 기록(`movie_views`, 2026-10-07) — "mova 랭킹"(많이 열어 본 영화)의 신호.

비로그인 방문자도 센다(사용자 결정). 같은 사람이 같은 영화를 하루 여러 번 열어도 1번 —
(movie_id, viewer_key, view_date) UNIQUE. viewer_key는 로그인이면 "u<users.id>", 비로그인이면
"v<방문자 UUID>"(프론트 쿠키 suvis_vid, 방문자 통계와 같은 값). 개인정보는 담지 않는다.
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel


class MovaMovieView(MovaModel):
    __tablename__ = "movie_views"
    __table_args__ = (
        UniqueConstraint("movie_id", "viewer_key", "view_date", name="uq_movie_views_daily"),
    )

    movie_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    viewer_key: Mapped[str] = mapped_column(String(64), nullable=False)
    view_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="KST 날짜")
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
