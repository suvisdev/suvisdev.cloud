from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SiteCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="고객(사이트) 이름")
    plan: Literal["free", "starter", "pro", "business"] = "starter"
    domains: list[str] = Field(
        default_factory=list, description="허용 도메인. 비면 Origin 검증 생략(개발용)"
    )


class SiteSchema(BaseModel):
    site_key: str
    name: str
    plan: str
    domains: list[str]
    active: bool
    created_at: datetime


class SiteIssuedSchema(SiteSchema):
    secret_key: str = Field(..., description="이 응답에서만 보인다 — 바로 안전하게 보관")


class EventSummarySchema(BaseModel):
    created_at: datetime
    site_key: str
    ip: str | None
    score: float
    verdict: str
    decided_by: str


class StatsSchema(BaseModel):
    event_count: int
    model_source: str
    recent: list[EventSummarySchema]
