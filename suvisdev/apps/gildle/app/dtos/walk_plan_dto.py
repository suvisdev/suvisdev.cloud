from __future__ import annotations

from dataclasses import dataclass

from gildle.app.dtos.route_option_dto import RouteOptionDto
from gildle.domain.services.walk_request import WalkRequest
from gildle.domain.value_objects.pet_place import PetPlace


@dataclass(frozen=True)
class WalkPlanDto:
    """산책 계획 — 무엇을 이해했는지 + 목표 길이 + 후보 경로."""

    understood: WalkRequest
    target_m: float
    max_m: float | None
    options: list[RouteOptionDto]
    # 문장의 목적지 종류("동물병원")를 코드가 고른 실제 장소. 못 찾으면 None(options도 빈다).
    destination_place: PetPlace | None = None
    # route에서 들를 곳(stops)이 있으면 모든 후보가 거치는 실제 장소(2026-09-29). 없으면 None.
    via_place: PetPlace | None = None
