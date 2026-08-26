from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from gildle.adapter.outbound.graph.osm_walk_graph_adapter import OsmWalkGraphAdapter
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.route_edge import RouteEdge

_PATCH_TARGET = "gildle.adapter.outbound.graph.osm_walk_graph_adapter._ox"


def _make_mock_graph() -> MagicMock:
    """osmnx가 반환하는 MultiDiGraph를 흉내내는 mock."""
    graph = MagicMock()
    graph.nodes = {
        1: {"y": 37.556, "x": 126.924},
        2: {"y": 37.557, "x": 126.925},
    }
    edge_data = {"length": 150.0, "name": "월드컵북로"}
    graph.edges.return_value = [(1, 2, 0, edge_data)]
    return graph


class TestLoadEdges:
    @patch(_PATCH_TARGET)
    def test_returns_route_edges(self, mock_ox_fn: MagicMock) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.graph_from_place.return_value = _make_mock_graph()
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

    @patch(_PATCH_TARGET)
    def test_no_name_sets_none(self, mock_ox_fn: MagicMock) -> None:
        mock_ox = mock_ox_fn.return_value
        graph = _make_mock_graph()
        graph.edges.return_value = [(1, 2, 0, {"length": 80.0})]
        mock_ox.graph_from_place.return_value = graph
        adapter = OsmWalkGraphAdapter()

        edges = adapter.load_edges("마포구, 서울, 대한민국")

        assert edges[0].road_name is None

    @patch(_PATCH_TARGET)
    def test_list_name_takes_first(self, mock_ox_fn: MagicMock) -> None:
        mock_ox = mock_ox_fn.return_value
        graph = _make_mock_graph()
        graph.edges.return_value = [
            (1, 2, 0, {"length": 100.0, "name": ["월드컵북로", "월드컵로"]})
        ]
        mock_ox.graph_from_place.return_value = graph
        adapter = OsmWalkGraphAdapter()

        edges = adapter.load_edges("마포구, 서울, 대한민국")

        assert edges[0].road_name == "월드컵북로"

    @patch(_PATCH_TARGET)
    def test_deduplicates_reverse_edges(self, mock_ox_fn: MagicMock) -> None:
        mock_ox = mock_ox_fn.return_value
        graph = _make_mock_graph()
        graph.edges.return_value = [
            (1, 2, 0, {"length": 150.0, "name": "월드컵북로"}),
            (2, 1, 0, {"length": 150.0, "name": "월드컵북로"}),
        ]
        mock_ox.graph_from_place.return_value = graph
        adapter = OsmWalkGraphAdapter()

        edges = adapter.load_edges("마포구, 서울, 대한민국")

        assert len(edges) == 1

    @patch(_PATCH_TARGET)
    def test_midpoint_is_average_of_nodes(self, mock_ox_fn: MagicMock) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.graph_from_place.return_value = _make_mock_graph()
        adapter = OsmWalkGraphAdapter()

        edges = adapter.load_edges("마포구, 서울, 대한민국")

        assert abs(edges[0].midpoint.latitude - (37.556 + 37.557) / 2) < 1e-6
        assert abs(edges[0].midpoint.longitude - (126.924 + 126.925) / 2) < 1e-6


class TestNearestNode:
    def test_finds_closest_node(self) -> None:
        edges = [
            RouteEdge(
                from_node="A",
                to_node="B",
                base_distance_m=100.0,
                midpoint=Coordinate(latitude=37.556, longitude=126.924),
                road_name=None,
            ),
        ]
        adapter = OsmWalkGraphAdapter()
        point = Coordinate(latitude=37.5561, longitude=126.9241)

        result = adapter.nearest_node(edges, point)

        assert result in ("A", "B")

    def test_empty_edges_returns_none(self) -> None:
        adapter = OsmWalkGraphAdapter()

        result = adapter.nearest_node([], Coordinate(latitude=37.5, longitude=126.9))

        assert result is None


class TestGraphML:
    @patch(_PATCH_TARGET)
    def test_save_graphml(self, mock_ox_fn: MagicMock, tmp_path: Path) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.graph_from_place.return_value = _make_mock_graph()
        adapter = OsmWalkGraphAdapter()

        out = adapter.save_graphml("마포구, 서울, 대한민국", tmp_path / "test.graphml")

        assert out == tmp_path / "test.graphml"
        mock_ox.save_graphml.assert_called_once()

    @patch(_PATCH_TARGET)
    def test_load_from_graphml(self, mock_ox_fn: MagicMock, tmp_path: Path) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.load_graphml.return_value = _make_mock_graph()
        adapter = OsmWalkGraphAdapter()

        edges = adapter.load_from_graphml(tmp_path / "test.graphml")

        assert len(edges) == 1
        mock_ox.load_graphml.assert_called_once_with(filepath=tmp_path / "test.graphml")
