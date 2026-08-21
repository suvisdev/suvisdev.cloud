"""download_osm_graph 단위 테스트 — osmnx mock 기반."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from gildle.scripts.download_osm_graph import download_walk_graph

_PATCH_OX = "gildle.scripts.download_osm_graph._ox"


def _make_mock_graph() -> MagicMock:
    graph = MagicMock()
    graph.nodes = {
        1: {"y": 37.528, "x": 126.933},
        2: {"y": 37.529, "x": 126.934},
    }
    graph.edges.return_value = [
        (1, 2, 0, {"length": 130.0, "name": "여의대로"}),
    ]
    return graph


class TestDownloadWalkGraph:
    @patch(_PATCH_OX)
    def test_calls_graph_from_point_with_center_and_dist(
        self, mock_ox_fn: MagicMock, tmp_path: Path
    ) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.graph_from_point.return_value = _make_mock_graph()
        output = tmp_path / "graph.graphml"

        download_walk_graph(center=(37.528, 126.933), dist_m=1500, output_path=output)

        mock_ox.graph_from_point.assert_called_once_with(
            (37.528, 126.933), dist=1500, network_type="walk"
        )

    @patch(_PATCH_OX)
    def test_saves_graphml_to_output_path(
        self, mock_ox_fn: MagicMock, tmp_path: Path
    ) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.graph_from_point.return_value = _make_mock_graph()
        output = tmp_path / "subdir" / "graph.graphml"

        result = download_walk_graph(center=(37.528, 126.933), dist_m=1500, output_path=output)

        assert result == output
        mock_ox.save_graphml.assert_called_once_with(
            mock_ox.graph_from_point.return_value, filepath=output
        )

    @patch(_PATCH_OX)
    def test_creates_parent_directory(
        self, mock_ox_fn: MagicMock, tmp_path: Path
    ) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.graph_from_point.return_value = _make_mock_graph()
        output = tmp_path / "deep" / "nested" / "graph.graphml"

        download_walk_graph(center=(37.528, 126.933), dist_m=1500, output_path=output)

        assert output.parent.exists()

    @patch(_PATCH_OX)
    def test_returns_node_and_edge_counts(
        self, mock_ox_fn: MagicMock, tmp_path: Path
    ) -> None:
        mock_ox = mock_ox_fn.return_value
        graph = _make_mock_graph()
        graph.__len__ = lambda self: 2
        mock_ox.graph_from_point.return_value = graph
        output = tmp_path / "graph.graphml"

        result = download_walk_graph(center=(37.528, 126.933), dist_m=1500, output_path=output)

        assert result == output
