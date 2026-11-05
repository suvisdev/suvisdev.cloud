from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TopicSchema(BaseModel):
    id: int
    label: str
    query: str


class AdminTopicSchema(TopicSchema):
    is_public: bool
    active: bool


class TopicCreateSchema(BaseModel):
    query: str = Field(..., min_length=1, max_length=100)
    label: str = Field(default="", max_length=50)
    is_public: bool = True


class TopicUpdateSchema(BaseModel):
    label: str | None = Field(default=None, max_length=50)
    is_public: bool | None = None
    active: bool | None = None


class ArticleSchema(BaseModel):
    """화면용 기사. 본문은 없다 — 제목·요약·원문 링크만 (저작권)."""

    id: int
    title: str
    url: str
    summary: str
    source_domain: str
    source_name: str | None
    published_at: datetime | None
    badge: Literal["none", "ai_disclosed", "ai_suspected"]
    reasons_ko: list[str]


class CollectReportSchema(BaseModel):
    topics: int
    feeds: int
    fetched: int
    irrelevant: int
    new_articles: int
    judged: int
    verdicts: dict[str, int]
    errors: list[str]
