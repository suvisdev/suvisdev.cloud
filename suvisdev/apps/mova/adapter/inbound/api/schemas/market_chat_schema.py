from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MovaChatRequest(BaseModel):
    message: str
    history: list[dict[str, Any]] = Field(default_factory=list)
    model: Literal["flash", "flash15", "pro"] | None = None
    user_id: int | None = None

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


class MovaChatResponseSchema(BaseModel):
    reply: str
    recommendations: list[MovaChatRecommendationSchema] = Field(default_factory=list)
    refined_query: str | None = None
    keywords: list[str] = Field(default_factory=list)
    intent_type: str | None = None
    search_filters: dict[str, Any] = Field(default_factory=dict)


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
