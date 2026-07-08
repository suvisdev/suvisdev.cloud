from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gildle.domain.value_objects.coordinate import Coordinate


@dataclass
class HazardZone:
    """결빙 교통사고 다발지역 엔티티.

    중심 좌표 + 반경(m)으로 원형 위험 영역을 표현하며, 사고 건수를 함께 보관한다.
    """

    id: int | None
    center: Coordinate
    radius_meters: float
    accident_count: int
    description: str

    def contains(self, point: Coordinate) -> bool:
        """주어진 좌표가 위험 영역(중심에서 반경 이내)에 들어오는지 판정한다."""
        return self.center.distance_to(point) <= self.radius_meters

    @classmethod
    def from_orm(cls, orm_obj: Any) -> HazardZone:
        """ORM 행 객체를 도메인 엔티티로 변환하는 팩토리(titanic from_orm 패턴)."""
        return cls(
            id=orm_obj.id,
            center=Coordinate(
                latitude=orm_obj.center_latitude,
                longitude=orm_obj.center_longitude,
            ),
            radius_meters=orm_obj.radius_meters,
            accident_count=orm_obj.accident_count,
            description=orm_obj.name,
        )
