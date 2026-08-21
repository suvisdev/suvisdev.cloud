"""build_graph_pipeline 통합 테스트 — mock OSM + 실 CSV 데이터."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gildle.scripts.build_graph_pipeline import run_pipeline
from gildle.scripts.compute_edge_scores import load_scored_edges

_PATCH_OX = "gildle.adapter.outbound.graph.osm_walk_graph_adapter._ox"

_YEOUIDO_CENTER = (37.5260, 126.9258)


def _make_mock_graph() -> MagicMock:
    graph = MagicMock()
    graph.nodes = {
        1: {"y": 37.5260, "x": 126.9245},
        2: {"y": 37.5265, "x": 126.9270},
        3: {"y": 37.5290, "x": 126.9140},
        4: {"y": 37.5295, "x": 126.9165},
    }
    graph.edges.return_value = [
        (1, 2, 0, {"length": 200.0, "name": "여의대로"}),
        (3, 4, 0, {"length": 150.0, "name": "국회대로"}),
        (2, 3, 0, {"length": 180.0}),
    ]
    return graph


def _write_sample_graphml(path: Path) -> None:
    path.write_text("<graphml/>")


def _tree_csv_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "yeongdeungpo_tree_segments.csv"


def _hazard_csv_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "icing_accident_zones.csv"


class TestRunPipeline:
    @patch(_PATCH_OX)
    def test_produces_scored_edges_json(
        self, mock_ox_fn: MagicMock, tmp_path: Path
    ) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.load_graphml.return_value = _make_mock_graph()
        graphml = tmp_path / "test.graphml"
        _write_sample_graphml(graphml)
        output = tmp_path / "scored.json"

        scored = run_pipeline(
            graphml_path=graphml,
            tree_csv=_tree_csv_path(),
            hazard_csv=_hazard_csv_path(),
            output_path=output,
            csv_encoding="cp949",
        )

        assert output.exists()
        assert len(scored) > 0

    @patch(_PATCH_OX)
    def test_yeouido_edge_gets_tree_score(
        self, mock_ox_fn: MagicMock, tmp_path: Path
    ) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.load_graphml.return_value = _make_mock_graph()
        graphml = tmp_path / "test.graphml"
        _write_sample_graphml(graphml)
        output = tmp_path / "scored.json"

        scored = run_pipeline(
            graphml_path=graphml,
            tree_csv=_tree_csv_path(),
            hazard_csv=_hazard_csv_path(),
            output_path=output,
            csv_encoding="cp949",
        )

        yeouido_edges = [e for e in scored if e.road_name == "여의대로"]
        assert len(yeouido_edges) > 0
        assert yeouido_edges[0].tree_score > 0.0

    @patch(_PATCH_OX)
    def test_all_scores_in_range(
        self, mock_ox_fn: MagicMock, tmp_path: Path
    ) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.load_graphml.return_value = _make_mock_graph()
        graphml = tmp_path / "test.graphml"
        _write_sample_graphml(graphml)
        output = tmp_path / "scored.json"

        scored = run_pipeline(
            graphml_path=graphml,
            tree_csv=_tree_csv_path(),
            hazard_csv=_hazard_csv_path(),
            output_path=output,
            csv_encoding="cp949",
        )

        for edge in scored:
            assert 0.0 <= edge.tree_score <= 1.0
            assert 0.0 <= edge.hazard_score <= 1.0
            assert 0.0 <= edge.dog_friendly_score <= 1.0

    @patch(_PATCH_OX)
    def test_saved_json_is_loadable(
        self, mock_ox_fn: MagicMock, tmp_path: Path
    ) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.load_graphml.return_value = _make_mock_graph()
        graphml = tmp_path / "test.graphml"
        _write_sample_graphml(graphml)
        output = tmp_path / "scored.json"

        run_pipeline(
            graphml_path=graphml,
            tree_csv=_tree_csv_path(),
            hazard_csv=_hazard_csv_path(),
            output_path=output,
            csv_encoding="cp949",
        )

        loaded = load_scored_edges(output)
        assert len(loaded) > 0

    @patch(_PATCH_OX)
    def test_idempotent(
        self, mock_ox_fn: MagicMock, tmp_path: Path
    ) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.load_graphml.return_value = _make_mock_graph()
        graphml = tmp_path / "test.graphml"
        _write_sample_graphml(graphml)
        output = tmp_path / "scored.json"

        run_pipeline(
            graphml_path=graphml,
            tree_csv=_tree_csv_path(),
            hazard_csv=_hazard_csv_path(),
            output_path=output,
            csv_encoding="cp949",
        )
        first = output.read_text()

        mock_ox.load_graphml.return_value = _make_mock_graph()
        run_pipeline(
            graphml_path=graphml,
            tree_csv=_tree_csv_path(),
            hazard_csv=_hazard_csv_path(),
            output_path=output,
            csv_encoding="cp949",
        )
        second = output.read_text()

        assert first == second

    @patch(_PATCH_OX)
    def test_dog_friendly_score_at_least_base(
        self, mock_ox_fn: MagicMock, tmp_path: Path
    ) -> None:
        mock_ox = mock_ox_fn.return_value
        mock_ox.load_graphml.return_value = _make_mock_graph()
        graphml = tmp_path / "test.graphml"
        _write_sample_graphml(graphml)
        output = tmp_path / "scored.json"

        scored = run_pipeline(
            graphml_path=graphml,
            tree_csv=_tree_csv_path(),
            hazard_csv=_hazard_csv_path(),
            output_path=output,
            csv_encoding="cp949",
        )

        for edge in scored:
            assert edge.dog_friendly_score >= 0.3 - 1e-9
