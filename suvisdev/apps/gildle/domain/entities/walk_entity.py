from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Walk:
    """완료된 산책 한 건. 저장·조회 사이에서 오가는 불변 값."""

    id: int | None
    user_id: int
    started_at: datetime
    ended_at: datetime
    distance_m: int
    duration_s: int
    path: list[list[float]]
    season_mode: str
    avg_shade_score: float | None = None
    memo: str | None = None

    def __post_init__(self) -> None:
        if self.ended_at < self.started_at:
            raise ValueError("종료 시각이 시작 시각보다 빠릅니다.")
        if self.distance_m < 0 or self.duration_s < 0:
            raise ValueError("거리·소요 시간은 음수일 수 없습니다.")
