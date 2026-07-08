from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from gildle.domain.value_objects.route_edge import RouteEdge


class RouteGraphPort(ABC):
    """보행로 그래프 빌드·최단경로 탐색 출력 포트.

    구현체(NetworkX 등)는 비즈니스 규칙을 모른 채 `weight_fn`을 기계적으로 적용한다.
    """

    @abstractmethod
    def build_graph(self, edges: list[RouteEdge]) -> Any:
        """간선 목록으로 그래프 자료구조를 만든다(구현체별 타입)."""
        ...

    @abstractmethod
    def find_shortest_path(
        self,
        graph: Any,
        start: str,
        end: str,
        weight_fn: Callable[[RouteEdge], float],
    ) -> list[str]:
        """`weight_fn`으로 각 간선 가중치를 구해 start→end 최단 경로(노드 id 목록)를 반환한다."""
        ...
