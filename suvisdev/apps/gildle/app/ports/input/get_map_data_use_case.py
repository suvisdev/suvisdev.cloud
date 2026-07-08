from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from gildle.domain.value_objects.season_mode import SeasonMode


class GetMapVisualizationDataUseCase(ABC):
    """모드별 지도 오버레이(가로수 구간/위험구역) 데이터 입력 포트."""

    @abstractmethod
    def execute(self, mode: SeasonMode) -> dict[str, Any]:
        ...
