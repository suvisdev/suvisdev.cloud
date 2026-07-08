import json

import pytest

from gildle.adapter.outbound.graph.sample_walk_graph_source import SampleWalkGraphSource
from gildle.domain.value_objects.coordinate import Coordinate


def _write_graph(path):
    rows = [
        {
            "from": "A",
            "to": "B",
            "from_lat": 37.50,
            "from_lng": 127.00,
            "to_lat": 37.52,
            "to_lng": 127.04,
            "base_distance_m": 200,
            "road_name": "여의대로",
        }
    ]
    path.write_text(json.dumps(rows), encoding="utf-8")


class TestSampleWalkGraphSource:
    def test_load_edges_builds_route_edges_with_midpoint(self, tmp_path):
        graph_file = tmp_path / "graph.json"
        _write_graph(graph_file)
        source = SampleWalkGraphSource(json_path=graph_file)

        edges = source.load_edges()

        assert len(edges) == 1
        assert edges[0].from_node == "A"
        assert edges[0].road_name == "여의대로"
        assert edges[0].midpoint.latitude == pytest.approx(37.51)
        assert edges[0].midpoint.longitude == pytest.approx(127.02)

    def test_nearest_node_returns_closest(self, tmp_path):
        graph_file = tmp_path / "graph.json"
        _write_graph(graph_file)
        source = SampleWalkGraphSource(json_path=graph_file)

        nearest = source.nearest_node(Coordinate(latitude=37.5001, longitude=127.0001))

        assert nearest == "A"

    def test_nearest_node_on_empty_graph_is_none(self, tmp_path):
        graph_file = tmp_path / "graph.json"
        graph_file.write_text("[]", encoding="utf-8")
        source = SampleWalkGraphSource(json_path=graph_file)

        assert source.nearest_node(Coordinate(latitude=37.5, longitude=127.0)) is None
