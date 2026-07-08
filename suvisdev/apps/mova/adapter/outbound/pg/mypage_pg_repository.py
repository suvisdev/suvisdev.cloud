from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_chat_orm import MovaChat
from mova.adapter.outbound.orm.market_picks_orm import MovaPick
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.app.dtos.mypage_dto import MypageDto, PickHistoryItem, SearchHistoryItem
from mova.app.ports.output.mypage_repository import MypageRepository
from viewer.adapter.outbound.orm.user_orm import User


class MypagePgRepository(MypageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_mypage(self, user_id: int) -> MypageDto:
        profile_row = (
            await self._session.execute(
                select(User.nickname, User.preferred_genres).where(User.id == user_id)
            )
        ).one_or_none()
        nickname = profile_row.nickname if profile_row else None
        preferred_genres: list[str] = list(profile_row.preferred_genres or []) if profile_row else []

        picks_rows = (
            await self._session.execute(
                select(MovaPick, MovaMovie.slug, MovaMovie.poster_url)
                .join(MovaMovie, MovaMovie.id == MovaPick.movie_id)
                .where(MovaPick.user_id == user_id)
                .order_by(desc(MovaPick.batch_at))
                .limit(12)
            )
        ).all()
        recent_picks = [
            PickHistoryItem(
                pick_id=row.MovaPick.id,
                title=row.MovaPick.title_snapshot,
                hook=row.MovaPick.hook,
                slug=row.slug,
                poster_url=row.poster_url,
                batch_at=row.MovaPick.batch_at,
                feedback=row.MovaPick.feedback,
            )
            for row in picks_rows
        ]

        chat_rows = (
            await self._session.execute(
                select(MovaChat.refined_query, MovaChat.created_at)
                .where(MovaChat.user_id == user_id)
                .order_by(desc(MovaChat.last_used_at))
                .limit(10)
            )
        ).all()
        recent_searches = [
            SearchHistoryItem(refined_query=row.refined_query, searched_at=row.created_at)
            for row in chat_rows
        ]

        return MypageDto(
            nickname=nickname,
            preferred_genres=preferred_genres,
            recent_picks=recent_picks,
            recent_searches=recent_searches,
        )
