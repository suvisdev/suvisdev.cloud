from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from gildle.app.dtos.walk_dto import WalkStats, WalkSummary
from gildle.domain.entities.walk_entity import Walk

_MAX_PATH_POINTS = 5000


class WalkCreateSchema(BaseModel):
    """산책 저장 요청. user_id는 받지 않는다 — 토큰의 principal로만 정한다."""

    started_at: datetime
    ended_at: datetime
    distance_m: int = Field(ge=0, le=500_000)
    duration_s: int = Field(ge=0, le=86_400)
    path: list[list[float]] = Field(default_factory=list, max_length=_MAX_PATH_POINTS)
    season_mode: str = Field(default="summer", max_length=16)
    avg_shade_score: float | None = Field(default=None, ge=0, le=1)
    memo: str | None = Field(default=None, max_length=200)


class WalkSummarySchema(BaseModel):
    id: int
    started_at: datetime
    ended_at: datetime
    distance_m: int
    duration_s: int
    season_mode: str
    avg_shade_score: float | None

    @classmethod
    def of(cls, s: WalkSummary) -> WalkSummarySchema:
        return cls(
            id=s.id,
            started_at=s.started_at,
            ended_at=s.ended_at,
            distance_m=s.distance_m,
            duration_s=s.duration_s,
            season_mode=s.season_mode,
            avg_shade_score=s.avg_shade_score,
        )


class WalkDetailSchema(WalkSummarySchema):
    path: list[list[float]]
    memo: str | None

    @classmethod
    def of_walk(cls, w: Walk) -> WalkDetailSchema:
        return cls(
            id=w.id or 0,
            started_at=w.started_at,
            ended_at=w.ended_at,
            distance_m=w.distance_m,
            duration_s=w.duration_s,
            season_mode=w.season_mode,
            avg_shade_score=w.avg_shade_score,
            path=w.path,
            memo=w.memo,
        )


class WalkStatsSchema(BaseModel):
    total_count: int
    total_distance_m: int
    total_duration_s: int

    @classmethod
    def of(cls, s: WalkStats) -> WalkStatsSchema:
        return cls(
            total_count=s.total_count,
            total_distance_m=s.total_distance_m,
            total_duration_s=s.total_duration_s,
        )
