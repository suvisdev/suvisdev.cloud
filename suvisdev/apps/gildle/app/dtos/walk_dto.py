from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from gildle.domain.entities.walk_entity import Walk


@dataclass(frozen=True, slots=True)
class WalkCreateCommand:
    """산책 저장 입력. user_id는 라우터가 principal에서 채운다(클라이언트 값 불신)."""

    user_id: int
    started_at: datetime
    ended_at: datetime
    distance_m: int
    duration_s: int
    path: list[list[float]]
    season_mode: str
    avg_shade_score: float | None = None
    memo: str | None = None

    def to_domain(self) -> Walk:
        return Walk(
            id=None,
            user_id=self.user_id,
            started_at=self.started_at,
            ended_at=self.ended_at,
            distance_m=self.distance_m,
            duration_s=self.duration_s,
            path=self.path,
            season_mode=self.season_mode,
            avg_shade_score=self.avg_shade_score,
            memo=self.memo,
        )


@dataclass(frozen=True, slots=True)
class WalkListQuery:
    user_id: int
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class WalkSummary:
    """목록용 요약 — 경로 좌표(path)는 상세 조회에서만 준다(응답 크기)."""

    id: int
    started_at: datetime
    ended_at: datetime
    distance_m: int
    duration_s: int
    season_mode: str
    avg_shade_score: float | None


@dataclass(frozen=True, slots=True)
class WalkStats:
    total_count: int
    total_distance_m: int
    total_duration_s: int
