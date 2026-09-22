"""좌표 기하 보조 — 방위각·거리로 좌표 옮기기(루프 경로 경유점 산출용).

`Coordinate`는 값 객체라 손대지 않고, 순수 함수로 둔다. 구면 근사(하버사인 역산).
"""

from __future__ import annotations

import math

from gildle.domain.value_objects.coordinate import Coordinate

_EARTH_RADIUS_M = 6_371_000.0


def offset(origin: Coordinate, bearing_deg: float, distance_m: float) -> Coordinate:
    """origin에서 bearing(북=0, 시계방향)으로 distance만큼 간 좌표."""
    lat1 = math.radians(origin.latitude)
    lng1 = math.radians(origin.longitude)
    brg = math.radians(bearing_deg)
    ang = distance_m / _EARTH_RADIUS_M
    lat2 = math.asin(
        math.sin(lat1) * math.cos(ang) + math.cos(lat1) * math.sin(ang) * math.cos(brg)
    )
    lng2 = lng1 + math.atan2(
        math.sin(brg) * math.sin(ang) * math.cos(lat1),
        math.cos(ang) - math.sin(lat1) * math.sin(lat2),
    )
    return Coordinate(latitude=math.degrees(lat2), longitude=math.degrees(lng2))
