from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoopCandidateDto:
    """출발점으로 돌아오는 산책 루프 후보 하나."""

    path: list[str]
    length_m: float
    overlap_ratio: float  # 같은 간선을 두 번 지난 길이 비율(0=왕복 없음)
    shade_ratio: float | None  # 여름 모드에서만
    bearing_deg: int  # 첫 경유점 방위각 — 디버그·다양성 표시용
