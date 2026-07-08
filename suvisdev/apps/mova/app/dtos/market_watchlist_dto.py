from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mova.adapter.inbound.api.schemas.market_watchlist_schema import (
        WatchlistSchema,
    )


@dataclass
class WatchlistItemDto:
    movie_id: int
    slug: str
    title: str
    release_year: str
    rating: float
    poster_url: str | None
    added_at: datetime


@dataclass
class WatchlistDto:
    items: list[WatchlistItemDto]

    def to_schema(self) -> WatchlistSchema:
        from mova.adapter.inbound.api.schemas.market_watchlist_schema import (
            WatchlistItemSchema,
            WatchlistSchema,
        )

        return WatchlistSchema(
            items=[
                WatchlistItemSchema(
                    movie_id=i.movie_id,
                    slug=i.slug,
                    title=i.title,
                    release_year=i.release_year,
                    rating=i.rating,
                    poster_url=i.poster_url,
                    added_at=i.added_at,
                )
                for i in self.items
            ],
            total=len(self.items),
        )
