from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from gildle.app.ports.output.hazard_zone_repository import HazardZoneRepository
from gildle.domain.entities.hazard_zone import HazardZone
from gildle.domain.value_objects.coordinate import Coordinate

# 한국도로교통공단 "결빙 교통사고 다발지역 정보" 실제 컬럼명.
# 시도/시군구는 결합 컬럼(예: "서울특별시 영등포구")이라 서울 필터는 접두사 매칭한다.
_COL_SIDO_SGG = "시도시군구명"
_COL_NAME = "지점명"
_COL_LAT = "위도"
_COL_LNG = "경도"
_COL_ACCIDENT = "사고건수"
# 반경 컬럼이 없으면 데이터셋 선정기준인 200m를 기본값으로 쓴다.
_COL_RADIUS = "반경"
_DEFAULT_RADIUS_M = 200.0
_SEOUL_PREFIX = "서울"


def _to_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _to_int(value: Any) -> int:
    if value is None or pd.isna(value):
        return 0
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (ValueError, TypeError):
        return 0


class TrafficAuthorityHazardZoneRepository(HazardZoneRepository):
    """HazardZoneRepository의 결빙 사고 다발지역 CSV 구현체.

    `시도시군구명`이 "서울"로 시작하는 행만 필터링해 중심좌표 + 반경으로 HazardZone을 만든다.
    반경 컬럼이 없으면(원 데이터셋 미제공) 선정기준인 200m를 적용한다.
    좌표가 결측이거나 범위를 벗어난 행은 Adapter 경계에서 제외한다.
    (결빙 다발지역 데이터는 위경도를 항상 포함하므로 Geocoding fallback은 두지 않는다.)
    """

    def __init__(self, csv_path: str | Path, encoding: str = "utf-8-sig") -> None:
        self._csv_path = Path(csv_path)
        self._encoding = encoding

    def find_all(self) -> list[HazardZone]:
        frame = pd.read_csv(self._csv_path, encoding=self._encoding)
        seoul = frame[
            frame[_COL_SIDO_SGG].astype(str).str.startswith(_SEOUL_PREFIX)
        ]
        zones: list[HazardZone] = []
        for position, row in enumerate(seoul.to_dict("records"), start=1):
            zone = self._to_zone(position, row)
            if zone is not None:
                zones.append(zone)
        return zones

    def _to_zone(self, position: int, row: dict[str, Any]) -> HazardZone | None:
        latitude = _to_float(row.get(_COL_LAT))
        longitude = _to_float(row.get(_COL_LNG))
        if latitude is None or longitude is None:
            return None  # 좌표 결측 → 제외

        try:
            center = Coordinate(latitude=latitude, longitude=longitude)
        except ValueError:
            return None  # 위경도 범위 이상값 → 제외

        radius = _to_float(row.get(_COL_RADIUS))
        return HazardZone(
            id=position,
            center=center,
            radius_meters=radius if radius is not None else _DEFAULT_RADIUS_M,
            accident_count=_to_int(row.get(_COL_ACCIDENT)),
            description=str(row.get(_COL_NAME, "")).strip(),
        )
