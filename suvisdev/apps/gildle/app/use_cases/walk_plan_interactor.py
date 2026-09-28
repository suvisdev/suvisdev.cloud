"""산책 계획 — mova 오케스트레이터와 같은 구조(2026-09-28).

① 이해: 7.8B가 자연어를 슬롯 JSON으로(WalkUnderstandingPort) → ② 검증: 문장 근거 규칙과
대조(walk_request.verify), 모델이 죽으면 규칙만으로 → ③ 폼 값 우선 → ④ 실행: 출발지로
돌아오는 루프(시간·거리·선호) 또는 도착지까지 경로 후보를 A*로. 모델은 길을 고르지 않는다.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping

from gildle.app.dtos.walk_plan_dto import WalkPlanDto
from gildle.app.ports.input.route_options_use_case import RouteOptionsUseCase
from gildle.app.ports.input.walk_plan_use_case import WalkPlanUseCase
from gildle.app.ports.output.walk_understanding_port import WalkUnderstandingPort
from gildle.domain.services.walk_request import WalkRequest, apply_form, parse_rules, verify
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge

logger = logging.getLogger(__name__)


class WalkPlanInteractor(WalkPlanUseCase):
    def __init__(
        self, options: RouteOptionsUseCase, understanding: WalkUnderstandingPort | None
    ) -> None:
        self._options = options
        self._understanding = understanding

    def understand(
        self,
        text: str | None,
        *,
        minutes: int | None,
        distance_km: float | None,
        preference: str | None,
        stops: list[str] | None,
        has_end: bool,
    ) -> WalkRequest:
        text = (text or "").strip()
        base = parse_rules(text)
        if text and self._understanding is not None:
            try:
                base = verify(self._understanding.understand(text), text)
            except Exception:  # noqa: BLE001 — 모델 장애는 규칙 이해로 폴백(mova와 같은 원칙)
                logger.warning("[WalkPlan] 이해 모델 실패 → 규칙 이해", exc_info=True)
        req = apply_form(
            base,
            minutes=minutes,
            distance_km=distance_km,
            preference=preference,
            stops=stops,
            has_end=has_end,
            has_text=bool(text),
        )
        logger.info("[WalkPlan] %r → %s", text[:60], req)
        return req

    def plan(
        self,
        request: WalkRequest,
        edges: list[RouteEdge],
        start: str,
        end: str | None,
        *,
        shade_lookup: Mapping[tuple[str, str], float] | None,
        elevation: Mapping[str, float] | None,
        nearest_node: Callable[[Coordinate], str | None],
    ) -> WalkPlanDto:
        target_m, max_m = request.targets()
        pref = request.preference
        if pref == "shade" and shade_lookup is None:
            pref = "green"  # 밤·그늘 데이터 없음 — 나무 그늘로 대신
        if pref in ("flat", "hilly") and not elevation:
            pref = "fast"
        if end is not None and request.kind == "route":
            options = self._options.plan(
                edges,
                start,
                end,
                shade_lookup=shade_lookup,
                recommended_kind=pref,
                elevation=elevation,
                extra_kinds=(pref,),
            )
        else:
            options = self._options.loops(
                edges,
                start,
                target_m=target_m,
                max_m=max_m,
                preference=pref,
                shade_lookup=shade_lookup,
                elevation=elevation,
                stop_categories=request.stops,
                nearest_node=nearest_node,
            )
        return WalkPlanDto(understood=request, target_m=target_m, max_m=max_m, options=options)
