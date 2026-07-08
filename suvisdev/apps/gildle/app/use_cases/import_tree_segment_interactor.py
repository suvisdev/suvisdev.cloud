from __future__ import annotations

from typing import Any

from gildle.app.ports.input.import_tree_segment_use_case import ImportTreeSegmentUseCase
from gildle.app.ports.output.geocoding_port import GeocodingPort
from gildle.domain.entities.tree_segment import TreeSegment
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.tree_species import TreeSpecies


class ImportTreeSegmentInteractor(ImportTreeSegmentUseCase):
    """원천 행 → TreeSegment 변환 유스케이스.

    1. 수종 필터: 인식 가능한 수종(벚/느티/은행)만 통과.
    2. 행의 위경도로 Coordinate 생성.
    3. 좌표 결측 행만 Geocoding fallback(예외 경로), 그래도 실패 시 제외.

    Geocoding 구현체(Kakao 등)는 GeocodingPort(ABC)로만 주입받는다(DIP). 없으면 None.
    """

    def __init__(self, geocoder: GeocodingPort | None) -> None:
        self._geocoder = geocoder

    def execute(self, raw_rows: list[dict[str, Any]]) -> list[TreeSegment]:
        segments: list[TreeSegment] = []
        for row in raw_rows:
            species = self._parse_species(row.get("species"))
            if species is None:
                continue  # 수종 필터

            coordinates = self._resolve_coordinates(row)
            if coordinates is None:
                continue  # 좌표 확보 실패 → 제외

            start, end = coordinates
            segments.append(
                TreeSegment(
                    id=None,
                    road_name=row.get("road_name"),
                    start=start,
                    end=end,
                    species=species,
                    quantity=int(row.get("quantity") or 0),
                    managing_agency=row.get("managing_agency") or "",
                )
            )
        return segments

    def _parse_species(self, raw: Any) -> TreeSpecies | None:
        if raw is None:
            return None
        try:
            return TreeSpecies.from_label(str(raw))
        except ValueError:
            return None

    def _resolve_coordinates(
        self, row: dict[str, Any]
    ) -> tuple[Coordinate, Coordinate] | None:
        start = self._coordinate_or_none(
            row.get("start_latitude"), row.get("start_longitude")
        )
        end = self._coordinate_or_none(
            row.get("end_latitude"), row.get("end_longitude")
        )
        if start is not None and end is not None:
            return start, end

        # 결측 보완(예외 경로): 주소를 geocoding → 시작=종료 단일 지점.
        if self._geocoder is not None:
            address = row.get("address")
            if address:
                point = self._geocoder.geocode(str(address))
                if point is not None:
                    return point, point
        return None

    def _coordinate_or_none(self, lat: Any, lng: Any) -> Coordinate | None:
        if lat in (None, "") or lng in (None, ""):
            return None
        try:
            return Coordinate(latitude=float(lat), longitude=float(lng))
        except (ValueError, TypeError):
            return None
