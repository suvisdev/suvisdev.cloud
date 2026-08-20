from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestGraphMLCache:
    @staticmethod
    def _make_mock_graph() -> MagicMock:
        graph = MagicMock()
        graph.nodes = {
            1: {"y": 37.556, "x": 126.924},
            2: {"y": 37.557, "x": 126.925},
        }
        graph.edges.return_value = [(1, 2, 0, {"length": 150.0, "name": "월드컵북로"})]
        return graph

    @patch("gildle.adapter.outbound.graph.osm_walk_graph_adapter.ox")
    def test_cache_miss_fetches_and_saves(self, mock_ox: MagicMock, tmp_path: Path) -> None:
        from gildle.adapter.outbound.graph.osm_walk_graph_adapter import OsmWalkGraphAdapter

        mock_ox.graph_from_place.return_value = self._make_mock_graph()
        adapter = OsmWalkGraphAdapter(cache_dir=tmp_path)

        edges = adapter.load_edges("마포구, 서울, 대한민국")

        assert len(edges) == 1
        mock_ox.graph_from_place.assert_called_once()
        mock_ox.save_graphml.assert_called_once()

    @patch("gildle.adapter.outbound.graph.osm_walk_graph_adapter.ox")
    def test_cache_hit_skips_network(self, mock_ox: MagicMock, tmp_path: Path) -> None:
        from gildle.adapter.outbound.graph.osm_walk_graph_adapter import OsmWalkGraphAdapter

        cache_file = tmp_path / "마포구_서울_대한민국.graphml"
        cache_file.write_text("<graphml/>")
        mock_ox.load_graphml.return_value = self._make_mock_graph()
        adapter = OsmWalkGraphAdapter(cache_dir=tmp_path)

        edges = adapter.load_edges("마포구, 서울, 대한민국")

        assert len(edges) == 1
        mock_ox.graph_from_place.assert_not_called()
        mock_ox.load_graphml.assert_called_once()

    @patch("gildle.adapter.outbound.graph.osm_walk_graph_adapter.ox")
    def test_no_cache_dir_always_fetches(self, mock_ox: MagicMock) -> None:
        from gildle.adapter.outbound.graph.osm_walk_graph_adapter import OsmWalkGraphAdapter

        mock_ox.graph_from_place.return_value = self._make_mock_graph()
        adapter = OsmWalkGraphAdapter(cache_dir=None)

        adapter.load_edges("마포구, 서울, 대한민국")

        mock_ox.graph_from_place.assert_called_once()
        mock_ox.save_graphml.assert_not_called()
