"""산책 계획 — mova 오케스트레이터와 같은 구조(2026-09-28).

① 이해: 7.8B가 자연어를 슬롯 JSON으로(WalkUnderstandingPort) → ② 검증: 문장 근거 규칙과
대조(walk_request.verify), 모델이 죽으면 규칙만으로 → ③ 폼 값 우선 → ④ 실행: 출발지로
돌아오는 루프(시간·거리·선호) 또는 도착지까지 경로 후보를 A*로. 모델은 길을 고르지 않는다.
목적지가 종류("동물병원으로 가는 최단 경로")로만 오면 출발지 근처에서 가장 가까운 그 종류 장소를
코드가 골라 도착지로 삼는다(2026-09-29) — 모델은 장소를 고르지 않는다.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping

from gildle.app.dtos.walk_plan_dto import WalkPlanDto
from gildle.app.ports.input.route_options_use_case import RouteOptionsUseCase
from gildle.app.ports.input.walk_plan_use_case import WalkPlanUseCase
from gildle.app.ports.output.pet_place_port import PetPlacePort
from gildle.app.ports.output.walk_understanding_port import WalkUnderstandingPort
from gildle.domain.services.walk_request import WalkRequest, apply_form, parse_rules, verify
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.pet_place import PetPlace
from gildle.domain.value_objects.route_edge import RouteEdge

logger = logging.getLogger(__name__)

_DESTINATION_RADIUS_M = 3000  # 산책으로 갈 만한 거리 안에서만 목적지를 찾는다


class WalkPlanInteractor(WalkPlanUseCase):
    def __init__(
        self,
        options: RouteOptionsUseCase,
        understanding: WalkUnderstandingPort | None,
        places: PetPlacePort | None = None,
    ) -> None:
        self._options = options
        self._understanding = understanding
        self._places = places

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
        start_point: Coordinate | None = None,
    ) -> WalkPlanDto:
        target_m, max_m = request.targets()
        pref = request.preference
        place: PetPlace | None = None
        if end is None and request.kind == "route" and request.destination:
            place = self._nearest_place(start_point, request.destination)
            end = nearest_node(place.coordinate) if place is not None else None
            if end is None:
                logger.info(
                    "[WalkPlan] 목적지 %s 근처 장소 없음(place=%s)", request.destination, place
                )
                return WalkPlanDto(
                    understood=request,
                    target_m=target_m,
                    max_m=max_m,
                    options=[],
                    destination_place=place,
                )
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
        return WalkPlanDto(
            understood=request,
            target_m=target_m,
            max_m=max_m,
            options=options,
            destination_place=place,
        )

    def _nearest_place(self, start: Coordinate | None, category: str) -> PetPlace | None:
        if start is None or self._places is None:
            return None
        try:
            found = self._places.search_around(start, _DESTINATION_RADIUS_M)
        except Exception:  # noqa: BLE001 — 장소 검색 장애는 "못 찾음"으로 정직하게
            logger.warning("[WalkPlan] 목적지 검색 실패", exc_info=True)
            return None
        same = [p for p in found if p.category == category]
        return min(same, key=lambda p: start.distance_to(p.coordinate), default=None)
