"""picks 도메인 Entity — AI 채팅 추천 작품 1건."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from mova.domain.value_objects.market_picks_vo import Feedback, PickRank


@dataclass(frozen=True)
class PickEntity:
    """한 번의 AI 채팅 응답에서 추천된 작품 1건 (배치당 최대 3건).

    ORM · Pydantic에 의존하지 않는다.
    PK `id`는 Repository가 반환한 뒤에만 존재 — 신규 생성 시 0 허용.
    user_id는 비로그인 추천 시 None.
    """

    id: int
    chat_id: int
    user_id: int | None
    movie_id: int
    pick_rank: PickRank
    hook: str | None
    title_snapshot: str
    batch_at: datetime
    feedback: Feedback | None

    @classmethod
    def from_orm(cls, orm: object) -> PickEntity:
        """SQLAlchemy ORM row(MovaPick) → Entity. ORM import는 이 팩토리 안에서만."""
        return cls(
            id=orm.id,
            chat_id=orm.chat_id,
            user_id=orm.user_id,
            movie_id=orm.movie_id,
            pick_rank=PickRank(orm.pick_rank),
            hook=orm.hook,
            title_snapshot=orm.title_snapshot,
            batch_at=orm.batch_at,
            feedback=Feedback.from_str(orm.feedback),
        )

    def is_top_pick(self) -> bool:
        """배치 내 1순위 추천 여부."""
        return self.pick_rank.is_top

    def is_liked(self) -> bool:
        return self.feedback is Feedback.LIKE

    def is_disliked(self) -> bool:
        return self.feedback is Feedback.DISLIKE

    def has_feedback(self) -> bool:
        """사용자가 like/dislike 반응을 남겼는지."""
        return self.feedback is not None


if __name__ == "__main__":
    from types import SimpleNamespace

    mock_orm = SimpleNamespace(
        id=1,
        chat_id=10,
        user_id=None,
        movie_id=42,
        pick_rank=1,
        hook="우울할 때 위로되는 영화",
        title_snapshot="인터스텔라",
        batch_at=datetime(2026, 6, 25, 12, 0, 0),
        feedback="like",
    )
    pick = PickEntity.from_orm(mock_orm)
    assert pick.pick_rank.value == 1
    assert pick.is_top_pick()
    assert pick.is_liked()
    assert not pick.is_disliked()
    assert pick.has_feedback()

    mock_no_fb = SimpleNamespace(**{**mock_orm.__dict__, "feedback": None, "pick_rank": 2})
    pick2 = PickEntity.from_orm(mock_no_fb)
    assert not pick2.has_feedback()
    assert not pick2.is_top_pick()

    print("market_picks_entity OK")
