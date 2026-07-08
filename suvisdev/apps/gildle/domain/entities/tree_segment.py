from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.tree_species import TreeSpecies


@dataclass
class TreeSegment:
    """가로수길 구간 엔티티.

    한 점이 아니라 시작~종료 좌표를 가진 **구간**으로 모델링한다.
    `id`로 식별되는 엔티티이므로 frozen이 아니다.
    """

    id: int | None
    road_name: str | None
    start: Coordinate
    end: Coordinate
    species: TreeSpecies
    quantity: int
    managing_agency: str

    def midpoint(self) -> Coordinate:
        """구간의 중간 좌표(시작·종료의 산술 평균)를 반환한다."""
        return Coordinate(
            latitude=(self.start.latitude + self.end.latitude) / 2,
            longitude=(self.start.longitude + self.end.longitude) / 2,
        )

    @classmethod
    def from_orm(cls, orm_obj: Any) -> TreeSegment:
        """ORM 행 객체를 도메인 엔티티로 변환하는 팩토리(titanic from_orm 패턴)."""
        return cls(
            id=orm_obj.id,
            road_name=orm_obj.road_name,
            start=Coordinate(
                latitude=orm_obj.start_latitude,
                longitude=orm_obj.start_longitude,
            ),
            end=Coordinate(
                latitude=orm_obj.end_latitude,
                longitude=orm_obj.end_longitude,
            ),
            species=TreeSpecies.from_label(orm_obj.species),
            quantity=orm_obj.quantity,
            managing_agency=orm_obj.managing_agency,
        )
