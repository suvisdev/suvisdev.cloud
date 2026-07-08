from __future__ import annotations

from typing import Any

from gildle.app.ports.input.get_map_data_use_case import (
    GetMapVisualizationDataUseCase,
)
from gildle.app.ports.output.hazard_zone_repository import HazardZoneRepository
from gildle.app.ports.output.tree_segment_repository import TreeSegmentRepository
from gildle.domain.entities.hazard_zone import HazardZone
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.season_mode import SeasonMode


class GetMapVisualizationDataInteractor(GetMapVisualizationDataUseCase):
    """모드별 지도 오버레이 데이터 유스케이스.

    - SPRING_AUTUMN: 가로수 구간 오버레이(봄/가을 산책 추천).
    - WINTER_SAFETY: 결빙 위험구역 오버레이(겨울 안전).
    """

    def __init__(
        self,
        tree_repository: TreeSegmentRepository,
        hazard_repository: HazardZoneRepository,
    ) -> None:
        self._tree_repository = tree_repository
        self._hazard_repository = hazard_repository

    def execute(self, mode: SeasonMode) -> dict[str, Any]:
        tree_segments: list[dict[str, Any]] = []
        hazard_zones: list[dict[str, Any]] = []

        if mode is SeasonMode.SPRING_AUTUMN:
            tree_segments = [
                self._serialize_segment(s) for s in self._tree_repository.find_all()
            ]
        elif mode is SeasonMode.WINTER_SAFETY:
            hazard_zones = [
                self._serialize_hazard(h) for h in self._hazard_repository.find_all()
            ]

        return {
            "mode": mode.value,
            "tree_segments": tree_segments,
            "hazard_zones": hazard_zones,
        }

    def _serialize_segment(self, segment: TreeSegment) -> dict[str, Any]:
        return {
            "id": segment.id,
            "road_name": segment.road_name,
            "species": segment.species.value,
            "quantity": segment.quantity,
            "start": self._serialize_coordinate(segment.start),
            "end": self._serialize_coordinate(segment.end),
            "midpoint": self._serialize_coordinate(segment.midpoint()),
        }

    def _serialize_hazard(self, hazard: HazardZone) -> dict[str, Any]:
        return {
            "id": hazard.id,
            "description": hazard.description,
            "radius_meters": hazard.radius_meters,
            "accident_count": hazard.accident_count,
            "center": self._serialize_coordinate(hazard.center),
        }

    def _serialize_coordinate(self, coordinate: Coordinate) -> dict[str, float]:
        return {
            "latitude": coordinate.latitude,
            "longitude": coordinate.longitude,
        }
