from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge


class WalkGraphPort(ABC):
    """OSM 보행 그래프 로드·조회·영속화 출력 포트.

    구현체(osmnx 등)는 비즈니스 규칙을 모른 채 그래프 데이터를 RouteEdge로 변환한다.
    """

    @abstractmethod
    def load_edges(self, place: str) -> list[RouteEdge]:
        """place(지역명)의 보행 그래프를 로드해 간선 목록을 반환한다."""
        ...

    @abstractmethod
    def nearest_node(self, edges: list[RouteEdge], point: Coordinate) -> str | None:
        """간선 목록에서 좌표에 가장 가까운 노드 id를 반환한다."""
        ...

    @abstractmethod
    def save_graphml(self, place: str, path: Path) -> Path:
        """place의 그래프를 GraphML로 저장하고 경로를 반환한다."""
        ...

    @abstractmethod
    def load_from_graphml(self, path: Path) -> list[RouteEdge]:
        """GraphML 파일에서 간선 목록을 로드한다."""
        ...
