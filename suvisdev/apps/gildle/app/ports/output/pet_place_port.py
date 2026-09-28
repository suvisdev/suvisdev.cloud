from __future__ import annotations

from abc import ABC, abstractmethod

from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.pet_place import PetPlace


class PetPlacePort(ABC):
    """반려동물 관련 장소 검색 출력 포트(카카오 로컬 등)."""

    @abstractmethod
    def search_around(self, center: Coordinate, radius_m: int) -> list[PetPlace]:
        """중심 반경 안의 동물병원·펫샵·용품점·애견카페. 키 없음·실패면 []."""
        ...
