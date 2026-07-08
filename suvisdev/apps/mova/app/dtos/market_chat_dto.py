"""채팅 DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChatRecommendationDto:
    id: str
    movie_id: int | None
    title: str
    year: str
    poster: str
    synopsis: str
    platform: str | None
    hook: str


@dataclass(frozen=True)
class ChatResponseDto:
    chat_id: int
    reply: str
    refined_query: str
    keywords: list[str]
    intent_type: str
    search_filters: dict
    recommendations: list[ChatRecommendationDto]

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.market_chat_schema import (
            MovaChatRecommendationSchema,
            MovaChatResponseSchema,
        )

        return MovaChatResponseSchema(
            reply=self.reply,
            recommendations=[
                MovaChatRecommendationSchema(
                    id=r.id,
                    movie_id=r.movie_id,
                    title=r.title,
                    year=r.year,
                    poster=r.poster,
                    synopsis=r.synopsis,
                    platform=r.platform,
                    hook=r.hook,
                )
                for r in self.recommendations
            ],
            refined_query=self.refined_query,
            keywords=self.keywords,
            intent_type=self.intent_type,
            search_filters=self.search_filters,
        )
