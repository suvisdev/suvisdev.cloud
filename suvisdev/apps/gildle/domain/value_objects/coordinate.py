from __future__ import annotations

import math
from dataclasses import dataclass

# 지구 평균 반지름(m) — Haversine 거리 계산 상수.
_EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class Coordinate:
    """위/경도 좌표 값 객체.

    - 위도는 -90~90, 경도는 -180~180 범위를 벗어나면 생성 시점에 거부한다.
    - 불변(frozen)이며, 거리 계산은 새 값을 반환할 뿐 자신을 바꾸지 않는다.
    """

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"위도는 -90~90 범위여야 합니다: {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"경도는 -180~180 범위여야 합니다: {self.longitude}")

    def distance_to(self, other: Coordinate) -> float:
        """다른 좌표까지의 거리를 Haversine 공식으로 계산해 미터로 반환한다."""
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        d_lat = math.radians(other.latitude - self.latitude)
        d_lng = math.radians(other.longitude - self.longitude)

        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return _EARTH_RADIUS_M * c
