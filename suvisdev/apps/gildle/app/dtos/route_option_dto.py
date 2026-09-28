from __future__ import annotations

from dataclasses import dataclass, field

from gildle.domain.value_objects.pet_place import PetPlace


@dataclass(frozen=True)
class RouteOptionDto:
    """경로 후보 하나 — 좌표·수치·고를 이유·경로 곁 반려동물 장소."""

    kind: str  # fast | shade | green | flat | hilly | via
    label: str
    reason: str
    highlights: list[str]
    recommended: bool
    path: list[str]
    coordinates: list[list[float]]
    length_m: float
    minutes: int
    extra_m: float
    shade_ratio: float | None
    green_ratio: float
    places: list[PetPlace] = field(default_factory=list)
    climb_m: float | None = None  # 진행 방향 누적 오르막(SRTM 고도, 없으면 None)
