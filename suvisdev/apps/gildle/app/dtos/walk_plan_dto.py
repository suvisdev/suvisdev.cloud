from __future__ import annotations

from dataclasses import dataclass

from gildle.app.dtos.route_option_dto import RouteOptionDto
from gildle.domain.services.walk_request import WalkRequest


@dataclass(frozen=True)
class WalkPlanDto:
    """산책 계획 — 무엇을 이해했는지 + 목표 길이 + 후보 경로."""

    understood: WalkRequest
    target_m: float
    max_m: float | None
    options: list[RouteOptionDto]
