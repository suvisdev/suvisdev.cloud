from __future__ import annotations

from abc import ABC, abstractmethod

from gildle.domain.entities.tree_segment import TreeSegment


class TreeSegmentRepository(ABC):
    """가로수길 구간 저장소 출력 포트.

    구현체를 CSV → PostgreSQL로 바꿔도 이 포트에 의존하는 Use Case는 바뀌지 않는다(OCP/DIP).
    """

    @abstractmethod
    def find_all(self) -> list[TreeSegment]:
        ...

    @abstractmethod
    def save_many(self, segments: list[TreeSegment]) -> None:
        ...
