from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from gildle.domain.entities.tree_segment import TreeSegment


class ImportTreeSegmentUseCase(ABC):
    """원천 행 데이터를 가로수길 구간 엔티티로 적재하는 입력 포트."""

    @abstractmethod
    def execute(self, raw_rows: list[dict[str, Any]]) -> list[TreeSegment]:
        ...
