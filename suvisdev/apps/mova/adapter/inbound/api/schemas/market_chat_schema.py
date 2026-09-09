from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MovaChatRequest(BaseModel):
    message: str
    history: list[dict[str, Any]] = Field(default_factory=list)
    model: Literal["flash", "flash15", "pro"] | None = None
    user_id: int | None = None
    conversation_id: int | None = Field(
        default=None,
        description="로그인 사용자의 기존 대화 스레드에 이어 붙일 때 지정. "
        "미지정이고 로그인 상태면 서버가 새 스레드를 생성해 응답에 id를 담아 돌려준다. "
        "비로그인은 이 값과 무관하게 저장하지 않는다.",
    )

    def history_dicts(self) -> list[dict[str, str]]:
        return [
            {"role": str(h.get("role", "")), "content": str(h.get("content", ""))}
            for h in self.history
        ]


class MovaChatRecommendationSchema(BaseModel):
    id: str
    movie_id: int | None = None
    title: str
    year: str = ""
    poster: str = ""
    synopsis: str = ""
    platform: str | None = None
    hook: str = ""


class MovaChatEvaluationSchema(BaseModel):
    """evaluate 트랙 정량 payload — 정성 서술은 reply에 담긴다."""

    movie_id: int
    review_count: int
    avg_rating: float | None = None
    tmdb_rating: float | None = None
    excerpts: list[str] = Field(default_factory=list)


class MovaChatTheaterSchema(BaseModel):
    name: str
    address: str = ""
    distance_m: int | None = None
    place_url: str = ""
    phone: str = ""


class MovaChatBookingLinkSchema(BaseModel):
    chain: str
    url: str


class MovaChatShowtimeSlotSchema(BaseModel):
    screen: str
    start_time: str
    end_time: str
    film_type: str = ""
    seats_available: int = 0
    seats_total: int = 0


class MovaChatCinemaShowtimeSchema(BaseModel):
    cinema_name: str
    slots: list[MovaChatShowtimeSlotSchema] = Field(default_factory=list)


class MovaChatBookingSchema(BaseModel):
    status: Literal["showing", "not_showing", "need_region"]
    region: str | None = None
    theaters: list[MovaChatTheaterSchema] = Field(default_factory=list)
    booking_links: list[MovaChatBookingLinkSchema] = Field(default_factory=list)
    showtimes: list[MovaChatCinemaShowtimeSchema] = Field(default_factory=list)


class MovaChatChoiceSchema(BaseModel):
    """모호한 제목의 후보 — 프론트가 클릭 칩으로 렌더해 사용자가 하나를 고른다."""

    title: str
    year: str = ""
    slug: str


class MovaChatResponseSchema(BaseModel):
    reply: str
    recommendations: list[MovaChatRecommendationSchema] = Field(default_factory=list)
    # 제목이 모호할 때(evaluate) 후보 목록. 있으면 프론트가 선택 칩을 띄운다.
    choices: list[MovaChatChoiceSchema] = Field(default_factory=list)
    refined_query: str | None = None
    keywords: list[str] = Field(default_factory=list)
    intent_type: str | None = None
    search_filters: dict[str, Any] = Field(default_factory=dict)
    conversation_id: int | None = Field(
        default=None,
        description="로그인 사용자에 한해 이 응답이 append된 대화 스레드 id. "
        "요청에 없어서 새로 만든 경우 생성된 id가 여기 담긴다. 비로그인은 항상 null.",
    )
    response_type: Literal["recommendation", "evaluation", "booking"] = Field(
        default="recommendation",
        description="응답 트랙(2026-08-28 3트랙). evaluation/booking이면 해당 payload가 함께 온다.",
    )
    evaluation: MovaChatEvaluationSchema | None = None
    booking: MovaChatBookingSchema | None = None


class MarketChatSchema(BaseModel):
    id: int = Field(0, description="Chat ID")
    name: str = Field("시나리오 작가 (Screenwriter)", description="Screenwriter's name")
    # 사용자의 말 속 숨은 의도를 정제된 문장으로 번역하는 작가. chat 테이블 관리

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "시나리오 작가 (Screenwriter)",
            }
        }
    }
