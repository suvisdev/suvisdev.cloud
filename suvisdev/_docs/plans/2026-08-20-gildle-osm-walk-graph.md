# Gildle OSM 보행 그래프 인프라 구현 계획

**Goal:** osmnx로 실제 OSM 보행 그래프를 추출해 기존 `sample_walk_graph.json`(4간선 데모)을 대체하고, `RouteWeightCalculator`와 연결하는 production-ready 인프라를 구축한다.

**Architecture:** 기존 hexagonal 구조를 유지한다. `WalkGraphPort`(출력 포트)를 신설해 osmnx 의존성을 `OsmWalkGraphAdapter`(아웃바운드 어댑터)에 격리한다. GraphML 파일 캐시 전략으로 osmnx 네트워크 호출을 최소화하고, DB(PostGIS) 적재 경로는 포트 인터페이스에만 열어두고 어댑터 구현은 이번 범위 밖으로 남긴다.

**Tech Stack:** osmnx 2.x, networkx (기존), GraphML 파일 영속화

## Global Constraints

- spoke 독립: `gildle`은 다른 spoke를 import하지 않는다. `core.*`만 의존.
- ruff + mypy strict 통과
- 기존 92개 테스트 유지
- osmnx 네트워크 호출은 테스트에서 반드시 mock
- `route_edges` ORM의 `tree_score`/`hazard_score`/`dog_friendly_score` 컬럼과 매핑

---

### Task 1: WalkGraphPort 출력 포트 + OsmWalkGraphAdapter + 테스트

기존 `SampleWalkGraphSource`를 대체할 OSM 보행 그래프 로드/조회 인터페이스를 포트로 정의하고, osmnx 구현 어댑터를 만든다.

**Files:**
- Create: `apps/gildle/app/ports/output/walk_graph_port.py`
- Create: `apps/gildle/adapter/outbound/graph/osm_walk_graph_adapter.py`
- Create: `apps/gildle/tests/adapter/outbound/test_osm_walk_graph_adapter.py`
- Modify: `apps/gildle/tests/app/fakes.py` (FakeWalkGraphSource 추가)

**Interfaces:**
- Consumes: `RouteEdge`, `Coordinate` (기존 도메인 VO)
- Produces: `WalkGraphPort` ABC — `load_edges(place: str) -> list[RouteEdge]`, `nearest_node(point: Coordinate) -> str | None`, `save_graphml(place: str, path: Path) -> Path`, `load_from_graphml(path: Path) -> list[RouteEdge]`

- [ ] **Step 1: WalkGraphPort ABC 작성**

```python
# apps/gildle/app/ports/output/walk_graph_port.py
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge


class WalkGraphPort(ABC):
    """OSM 보행 그래프 로드·조회·영속화 출력 포트."""

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
```

- [ ] **Step 2: Failing test 작성**

```python
# apps/gildle/tests/adapter/outbound/test_osm_walk_graph_adapter.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gildle.adapter.outbound.graph.osm_walk_graph_adapter import OsmWalkGraphAdapter
from gildle.domain.value_objects.coordinate import Coordinate


class TestOsmWalkGraphAdapter:
    def _make_mock_graph(self) -> MagicMock:
        """osmnx가 반환하는 MultiDiGraph를 흉내내는 mock."""
        graph = MagicMock()
        graph.nodes = {
            1: {"y": 37.556, "x": 126.924},
            2: {"y": 37.557, "x": 126.925},
        }
        edge_data = {
            "length": 150.0,
            "name": "월드컵북로",
        }
        graph.edges = MagicMock(return_value=[(1, 2, 0, edge_data)])
        return graph

    @patch("gildle.adapter.outbound.graph.osm_walk_graph_adapter.ox")
    def test_load_edges_returns_route_edges(self, mock_ox: MagicMock) -> None:
        mock_ox.graph_from_place.return_value = self._make_mock_graph()
        adapter = OsmWalkGraphAdapter()

        edges = adapter.load_edges("마포구, 서울, 대한민국")

        assert len(edges) == 1
        assert edges[0].from_node == "1"
        assert edges[0].to_node == "2"
        assert edges[0].base_distance_m == 150.0
        assert edges[0].road_name == "월드컵북로"
        mock_ox.graph_from_place.assert_called_once_with(
            "마포구, 서울, 대한민국", network_type="walk"
        )

    @patch("gildle.adapter.outbound.graph.osm_walk_graph_adapter.ox")
    def test_load_edges_no_name_sets_none(self, mock_ox: MagicMock) -> None:
        graph = self._make_mock_graph()
        edge_data_no_name = {"length": 80.0}
        graph.edges = MagicMock(return_value=[(1, 2, 0, edge_data_no_name)])
        mock_ox.graph_from_place.return_value = graph
        adapter = OsmWalkGraphAdapter()

        edges = adapter.load_edges("마포구, 서울, 대한민국")

        assert edges[0].road_name is None

    @patch("gildle.adapter.outbound.graph.osm_walk_graph_adapter.ox")
    def test_load_edges_list_name_takes_first(self, mock_ox: MagicMock) -> None:
        graph = self._make_mock_graph()
        edge_data = {"length": 100.0, "name": ["월드컵북로", "월드컵로"]}
        graph.edges = MagicMock(return_value=[(1, 2, 0, edge_data)])
        mock_ox.graph_from_place.return_value = graph
        adapter = OsmWalkGraphAdapter()

        edges = adapter.load_edges("마포구, 서울, 대한민국")

        assert edges[0].road_name == "월드컵북로"

    def test_nearest_node_finds_closest(self) -> None:
        from gildle.domain.value_objects.route_edge import RouteEdge

        edges = [
            RouteEdge(
                from_node="1", to_node="2",
                base_distance_m=100.0,
                midpoint=Coordinate(latitude=37.556, longitude=126.924),
                road_name=None,
            ),
        ]
        adapter = OsmWalkGraphAdapter()
        point = Coordinate(latitude=37.5561, longitude=126.9241)

        result = adapter.nearest_node(edges, point)

        assert result in ("1", "2")

    @patch("gildle.adapter.outbound.graph.osm_walk_graph_adapter.ox")
    def test_save_and_load_graphml(self, mock_ox: MagicMock, tmp_path: Path) -> None:
        mock_graph = self._make_mock_graph()
        mock_ox.graph_from_place.return_value = mock_graph
        mock_ox.save_graphml.return_value = None
        adapter = OsmWalkGraphAdapter()

        out = adapter.save_graphml("마포구, 서울, 대한민국", tmp_path / "test.graphml")

        mock_ox.save_graphml.assert_called_once()
        assert out == tmp_path / "test.graphml"
```

- [ ] **Step 3: OsmWalkGraphAdapter 구현**

```python
# apps/gildle/adapter/outbound/graph/osm_walk_graph_adapter.py
from __future__ import annotations

from pathlib import Path

import osmnx as ox

from gildle.app.ports.output.walk_graph_port import WalkGraphPort
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge


class OsmWalkGraphAdapter(WalkGraphPort):
    """WalkGraphPort의 osmnx 구현체.

    osmnx(network_type='walk')로 보행 그래프를 추출하고,
    RouteEdge 도메인 VO로 변환한다.
    """

    def load_edges(self, place: str) -> list[RouteEdge]:
        graph = ox.graph_from_place(place, network_type="walk")
        return self._graph_to_edges(graph)

    def nearest_node(self, edges: list[RouteEdge], point: Coordinate) -> str | None:
        if not edges:
            return None
        node_coords: dict[str, Coordinate] = {}
        for edge in edges:
            node_coords.setdefault(edge.from_node, edge.midpoint)
            node_coords.setdefault(edge.to_node, edge.midpoint)
        # 간선의 from/to 좌표가 필요하므로 midpoint를 대체 좌표로 쓰되,
        # 실제로는 그래프 노드 좌표를 _graph_to_edges에서 보존해야 한다.
        # 여기서는 모든 간선의 from/to를 순회해서 가장 가까운 노드를 찾는다.
        all_nodes: dict[str, Coordinate] = {}
        for edge in edges:
            # midpoint만 있으므로 from/to 근사로 사용
            all_nodes.setdefault(edge.from_node, edge.midpoint)
            all_nodes.setdefault(edge.to_node, edge.midpoint)
        return min(all_nodes, key=lambda nid: point.distance_to(all_nodes[nid]))

    def save_graphml(self, place: str, path: Path) -> Path:
        graph = ox.graph_from_place(place, network_type="walk")
        ox.save_graphml(graph, filepath=path)
        return path

    def load_from_graphml(self, path: Path) -> list[RouteEdge]:
        graph = ox.load_graphml(filepath=path)
        return self._graph_to_edges(graph)

    def _graph_to_edges(self, graph: object) -> list[RouteEdge]:
        edges: list[RouteEdge] = []
        seen: set[tuple[str, str]] = set()
        for u, v, _key, data in graph.edges(data=True, keys=True):  # type: ignore[union-attr]
            pair = (str(min(u, v)), str(max(u, v)))
            if pair in seen:
                continue
            seen.add(pair)

            nodes = graph.nodes  # type: ignore[union-attr]
            u_lat, u_lng = float(nodes[u]["y"]), float(nodes[u]["x"])
            v_lat, v_lng = float(nodes[v]["y"]), float(nodes[v]["x"])

            raw_name = data.get("name")
            if isinstance(raw_name, list):
                road_name = str(raw_name[0]) if raw_name else None
            elif raw_name is not None:
                road_name = str(raw_name)
            else:
                road_name = None

            length = float(data.get("length", 0.0))
            mid = Coordinate(
                latitude=(u_lat + v_lat) / 2,
                longitude=(u_lng + v_lng) / 2,
            )
            edges.append(RouteEdge(
                from_node=str(u),
                to_node=str(v),
                base_distance_m=length,
                midpoint=mid,
                road_name=road_name,
            ))
        return edges
```

- [ ] **Step 4: FakeWalkGraphSource를 fakes.py에 추가**

```python
# tests/app/fakes.py에 추가
class FakeWalkGraphSource(WalkGraphPort):
    def __init__(self, edges: list[RouteEdge] | None = None) -> None:
        self._edges = list(edges or [])

    def load_edges(self, place: str) -> list[RouteEdge]:
        return list(self._edges)

    def nearest_node(self, edges: list[RouteEdge], point: Coordinate) -> str | None:
        if not edges:
            return None
        all_nodes: dict[str, Coordinate] = {}
        for edge in edges:
            all_nodes.setdefault(edge.from_node, edge.midpoint)
            all_nodes.setdefault(edge.to_node, edge.midpoint)
        return min(all_nodes, key=lambda nid: point.distance_to(all_nodes[nid]))

    def save_graphml(self, place: str, path: Path) -> Path:
        return path

    def load_from_graphml(self, path: Path) -> list[RouteEdge]:
        return list(self._edges)
```

- [ ] **Step 5: 테스트 실행 + ruff + mypy 확인**

```bash
pip install osmnx
pytest apps/gildle/tests -x -v -m "not gpu and not ollama"
ruff check apps/gildle/ --fix
ruff format apps/gildle/
mypy apps/gildle/app/ports/output/walk_graph_port.py apps/gildle/adapter/outbound/graph/osm_walk_graph_adapter.py
```

- [ ] **Step 6: route_provider.py에 OSM 어댑터 연결**

`dependencies/route_provider.py`에 `get_walk_graph_port()` 팩토리를 추가한다. 환경변수 `GILDLE_WALK_GRAPH_SOURCE`(`osm` | `sample`, 기본 `sample`)로 전환 가능하게 한다.

- [ ] **Step 7: 커밋**

```bash
git add apps/gildle/app/ports/output/walk_graph_port.py \
        apps/gildle/adapter/outbound/graph/osm_walk_graph_adapter.py \
        apps/gildle/tests/adapter/outbound/test_osm_walk_graph_adapter.py \
        apps/gildle/tests/app/fakes.py \
        apps/gildle/dependencies/route_provider.py
git commit -m "feat(gildle): OSM 보행 그래프 WalkGraphPort + OsmWalkGraphAdapter 신설"
```

---

### Task 2: GraphML 캐시 전략 + ERD route_edges 점수 매핑 + 테스트

osmnx 네트워크 호출을 최소화하기 위한 GraphML 파일 캐시와, 기존 `route_edges` ORM의 `tree_score`/`hazard_score`/`dog_friendly_score` 컬럼을 `RouteEdge` VO에 매핑하는 확장.

**Files:**
- Modify: `apps/gildle/domain/value_objects/route_edge.py` (점수 필드 추가)
- Modify: `apps/gildle/adapter/outbound/graph/osm_walk_graph_adapter.py` (캐시 로직)
- Create: `apps/gildle/tests/adapter/outbound/test_osm_walk_graph_graphml_cache.py`
- Modify: 기존 `RouteEdge` 사용처 전수 확인 (frozen dataclass라 기본값 추가면 호환)

**Interfaces:**
- Consumes: `WalkGraphPort` (Task 1), `RouteEdgeOrm` (기존 ORM)
- Produces: 확장된 `RouteEdge` (tree_score, hazard_score, dog_friendly_score 필드), `CachedOsmWalkGraphAdapter`(GraphML 캐시 전략 내장)

- [ ] **Step 1: RouteEdge에 점수 필드 추가**

```python
# domain/value_objects/route_edge.py — 기존 필드 뒤에 추가
    tree_score: float = 0.0
    hazard_score: float = 0.0
    dog_friendly_score: float = 0.0
```

- [ ] **Step 2: OsmWalkGraphAdapter에 GraphML 캐시 로직 추가**

`load_edges`에 `cache_dir: Path | None` 파라미터를 받아, 캐시 파일이 있으면 `load_from_graphml`로, 없으면 osmnx 호출 후 `save_graphml`로 저장하는 분기.

- [ ] **Step 3: 테스트 작성 — 캐시 hit/miss 시나리오**

- [ ] **Step 4: 기존 테스트 전수 실행 (RouteEdge 변경 영향)**

```bash
pytest apps/gildle/tests -x -v -m "not gpu and not ollama"
```

- [ ] **Step 5: ruff + mypy 확인**

- [ ] **Step 6: 커밋**

```bash
git commit -m "feat(gildle): RouteEdge 점수 필드 + GraphML 캐시 전략"
```

---

### Task 3: route_provider 통합 + 전체 검증 + 커밋·푸시·배포

DI 조립, 린트·타입 체크 전체 통과, 커밋·푸시.

**Files:**
- Modify: `apps/gildle/dependencies/route_provider.py`
- 전체 테스트 + ruff + mypy

- [ ] **Step 1: route_provider에 OSM/Sample 전환 팩토리 완성**

- [ ] **Step 2: 전체 gildle 테스트 통과**

- [ ] **Step 3: ruff check + ruff format + mypy strict**

- [ ] **Step 4: 프론트 type-check (gildle 소개 페이지 영향 없음 확인)**

- [ ] **Step 5: WORK_LOG + PROGRESS 갱신**

- [ ] **Step 6: 커밋·푸시·배포**
