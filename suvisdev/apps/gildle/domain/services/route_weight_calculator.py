from __future__ import annotations

from gildle.domain.entities.hazard_zone import HazardZone
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.domain.value_objects.route_weight import RouteWeight
from gildle.domain.value_objects.season_mode import SeasonMode

# 가중치 규칙 상수.
_SPRING_DISCOUNT_RATE = 0.3  # 보너스 수종 구간 30% 감면
_WINTER_PENALTY_RATE = 5.0  # 위험구역 근처 500% 증가(6배)
_PROXIMITY_MATCH_M = 10.0  # 도로명 매칭 실패 시 좌표 근접 보조 기준
_HAZARD_NEAR_M = 20.0  # 위험구역 근접 판정 기준


class RouteWeightCalculator:
    """모드별 간선 가중치 규칙을 캡슐화한 도메인 서비스.

    외부 라이브러리에 의존하지 않는 순수 비즈니스 규칙이다.
    """

    def calculate_edge_weight(
        self,
        edge: RouteEdge,
        mode: SeasonMode,
        nearby_segments: list[TreeSegment],
        nearby_hazards: list[HazardZone],
    ) -> RouteWeight:
        """간선 하나의 모드별 가중치를 계산한다.

        - SPRING_AUTUMN: 보너스 수종(벚나무/느티나무) 가로수길과 매칭되면 30% 감면.
        - WINTER_SAFETY: 결빙 위험구역이 간선 중간 좌표 20m 이내면 500% 증가.
        """
        base = RouteWeight(edge.base_distance_m)

        if mode is SeasonMode.SPRING_AUTUMN:
            if self._matches_bonus_tree(edge, nearby_segments):
                return base.apply_discount(_SPRING_DISCOUNT_RATE)
            return base

        if mode is SeasonMode.WINTER_SAFETY:
            if self._near_hazard(edge, nearby_hazards):
                return base.apply_penalty(_WINTER_PENALTY_RATE)
            return base

        return base

    def _matches_bonus_tree(
        self, edge: RouteEdge, segments: list[TreeSegment]
    ) -> bool:
        """보너스 수종 구간 매칭. 도로명 일치(우선) → 좌표 근접(보조) 순으로 본다."""
        bonus_segments = [s for s in segments if s.species.is_bonus_species]

        # (a) 우선: 도로명이 있고 같은 도로명 구간이 존재하면 매칭.
        if edge.road_name is not None:
            for segment in bonus_segments:
                if segment.road_name == edge.road_name:
                    return True

        # (b) 보조: 도로명이 없거나 일치 실패 시 중간 좌표 10m 이내면 매칭.
        for segment in bonus_segments:
            if edge.midpoint.distance_to(segment.midpoint()) <= _PROXIMITY_MATCH_M:
                return True

        return False

    def _near_hazard(self, edge: RouteEdge, hazards: list[HazardZone]) -> bool:
        """간선 중간 좌표가 어느 위험구역 중심에서 20m 이내인지 판정한다."""
        for hazard in hazards:
            if edge.midpoint.distance_to(hazard.center) <= _HAZARD_NEAR_M:
                return True
        return False
