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
class ReviewAggregateDto:
    """movie 1편의 자체 리뷰 집계 — ReviewAggregationPort 반환형."""

    review_count: int
    avg_rating: float | None
    excerpts: list[str]


@dataclass(frozen=True)
class ChatEvaluationDto:
    """evaluate 트랙 payload — 정량 지표는 여기, 정성 서술은 reply 텍스트에."""

    movie_id: int
    review_count: int
    avg_rating: float | None
    tmdb_rating: float | None
    excerpts: list[str]


@dataclass(frozen=True)
class ChatTheaterDto:
    name: str
    address: str
    distance_m: int | None
    place_url: str
    phone: str


@dataclass(frozen=True)
class ChatBookingLinkDto:
    chain: str
    url: str


@dataclass(frozen=True)
class ChatBookingDto:
    """booking 트랙 payload. status: showing | not_showing | need_region."""

    status: str
    region: str | None
    theaters: list[ChatTheaterDto]
    booking_links: list[ChatBookingLinkDto]


@dataclass(frozen=True)
class ChatResponseDto:
    chat_id: int
    reply: str
    refined_query: str
    keywords: list[str]
    intent_type: str
    search_filters: dict
    recommendations: list[ChatRecommendationDto]
    conversation_id: int | None = None
    # 2026-08-28 3트랙: recommendation(기존) | evaluation | booking.
    # 구 프론트는 이 필드를 모른 채 recommendations만 렌더해도 동작한다(하위호환).
    response_type: str = "recommendation"
    evaluation: ChatEvaluationDto | None = None
    booking: ChatBookingDto | None = None

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.market_chat_schema import (
            MovaChatBookingLinkSchema,
            MovaChatBookingSchema,
            MovaChatEvaluationSchema,
            MovaChatRecommendationSchema,
            MovaChatResponseSchema,
            MovaChatTheaterSchema,
        )

        evaluation = (
            MovaChatEvaluationSchema(
                movie_id=self.evaluation.movie_id,
                review_count=self.evaluation.review_count,
                avg_rating=self.evaluation.avg_rating,
                tmdb_rating=self.evaluation.tmdb_rating,
                excerpts=self.evaluation.excerpts,
            )
            if self.evaluation
            else None
        )
        booking = (
            MovaChatBookingSchema(
                status=self.booking.status,
                region=self.booking.region,
                theaters=[
                    MovaChatTheaterSchema(
                        name=t.name,
                        address=t.address,
                        distance_m=t.distance_m,
                        place_url=t.place_url,
                        phone=t.phone,
                    )
                    for t in self.booking.theaters
                ],
                booking_links=[
                    MovaChatBookingLinkSchema(chain=link.chain, url=link.url)
                    for link in self.booking.booking_links
                ],
            )
            if self.booking
            else None
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
            conversation_id=self.conversation_id,
            response_type=self.response_type,
            evaluation=evaluation,
            booking=booking,
        )
