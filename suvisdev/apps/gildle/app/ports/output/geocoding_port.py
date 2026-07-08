from __future__ import annotations

from abc import ABC, abstractmethod

from gildle.domain.value_objects.coordinate import Coordinate


class GeocodingPort(ABC):
    """주소 → 좌표 변환 출력 포트 (좌표 결측 보완용 fallback)."""

    @abstractmethod
    def geocode(self, address: str) -> Coordinate | None:
        """주소를 좌표로 변환한다. 실패/결과 없음이면 None."""
        ...
