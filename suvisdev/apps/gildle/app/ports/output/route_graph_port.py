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

    def find_shortest_path_time_dependent(
        self,
        graph: Any,
        start: str,
        end: str,
        weight_fn_t: Callable[[RouteEdge, float], float],
    ) -> list[str]:
        """간선 가중치가 **그 간선에 도달하기까지 걸은 거리(m)**에 따라 달라지는 탐색.

        여름 그늘은 걷는 동안 슬롯이 바뀐다(09시 0.93 → 15시 0.06인 거리가 있다,
        `_docs/GILDLE_ROUTING_ALGORITHM.md` §1-③). 기본 구현은 시각을 무시하고
        출발 시점(0m) 가중치로 일반 탐색을 한다 — networkx 구현체가 그렇다.
        자체 다익스트라 구현체가 이를 덮어쓴다.
        """
        return self.find_shortest_path(graph, start, end, lambda e: weight_fn_t(e, 0.0))
