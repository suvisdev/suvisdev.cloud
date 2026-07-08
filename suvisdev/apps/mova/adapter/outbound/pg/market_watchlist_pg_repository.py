from __future__ import annotations

from sqlalchemy import delete, desc, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_watchlist_orm import MovaWatchlist
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.app.dtos.market_watchlist_dto import WatchlistDto, WatchlistItemDto
from mova.app.ports.output.market_watchlist_repository import WatchlistRepository


class WatchlistPgRepository(WatchlistRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_watchlist(self, user_id: int) -> WatchlistDto:
        rows = (
            await self._session.execute(
                select(MovaWatchlist, MovaMovie.slug, MovaMovie.title, MovaMovie.release_year, MovaMovie.rating, MovaMovie.poster_url)
                .join(MovaMovie, MovaMovie.id == MovaWatchlist.movie_id)
                .where(MovaWatchlist.user_id == user_id)
                .order_by(desc(MovaWatchlist.added_at))
            )
        ).all()
        return WatchlistDto(
            items=[
                WatchlistItemDto(
                    movie_id=row.MovaWatchlist.movie_id,
                    slug=row.slug,
                    title=row.title,
                    release_year=row.release_year or "",
                    rating=float(row.rating),
                    poster_url=row.poster_url,
                    added_at=row.MovaWatchlist.added_at,
                )
                for row in rows
            ]
        )

    async def add(self, user_id: int, movie_id: int) -> None:
        stmt = (
            insert(MovaWatchlist)
            .values(user_id=user_id, movie_id=movie_id)
            .on_conflict_do_nothing(constraint="uq_watchlist_user_movie")
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def remove(self, user_id: int, movie_id: int) -> None:
        await self._session.execute(
            delete(MovaWatchlist).where(
                MovaWatchlist.user_id == user_id,
                MovaWatchlist.movie_id == movie_id,
            )
        )
        await self._session.commit()

    async def is_in_watchlist(self, user_id: int, movie_id: int) -> bool:
        result = await self._session.execute(
            select(
                exists().where(
                    MovaWatchlist.user_id == user_id,
                    MovaWatchlist.movie_id == movie_id,
                )
            )
        )
        return bool(result.scalar())
