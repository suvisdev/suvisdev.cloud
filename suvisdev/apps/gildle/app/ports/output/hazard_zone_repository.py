from __future__ import annotations

from abc import ABC, abstractmethod

from gildle.domain.entities.hazard_zone import HazardZone


class HazardZoneRepository(ABC):
    """결빙 사고 다발 위험구역 저장소 출력 포트."""

    @abstractmethod
    def find_all(self) -> list[HazardZone]:
        ...
