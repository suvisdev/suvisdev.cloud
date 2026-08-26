"""import_to_db 단위 테스트 — SQLite in-memory DB."""

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import gildle.adapter.outbound.orm.hazard_zone_orm  # noqa: F401
import gildle.adapter.outbound.orm.route_edge_orm  # noqa: F401
import gildle.adapter.outbound.orm.route_node_orm  # noqa: F401
import gildle.adapter.outbound.orm.tree_segment_orm  # noqa: F401
from gildle.adapter.outbound.orm.base import GildleBase
from gildle.adapter.outbound.orm.hazard_zone_orm import HazardZoneOrm
from gildle.adapter.outbound.orm.route_edge_orm import RouteEdgeOrm
from gildle.adapter.outbound.orm.route_node_orm import RouteNodeOrm
from gildle.adapter.outbound.orm.tree_segment_orm import TreeSegmentOrm
from gildle.scripts.import_to_db import (
    import_hazard_zones,
    import_scored_edges,
    import_tree_segments,
)


def _make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    GildleBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    return factory()


def _tree_csv_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "yeongdeungpo_tree_segments.csv"


def _hazard_csv_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "icing_accident_zones.csv"


def _make_scored_edges_json(tmp_path: Path) -> Path:
    edges = [
        {
            "from_node": "100",
            "to_node": "200",
            "base_distance_m": 150.0,
            "midpoint_lat": 37.527,
            "midpoint_lng": 126.926,
            "road_name": "여의대로",
            "tree_score": 0.8,
            "hazard_score": 0.2,
            "dog_friendly_score": 0.86,
        },
        {
            "from_node": "200",
            "to_node": "300",
            "base_distance_m": 200.0,
            "midpoint_lat": 37.529,
            "midpoint_lng": 126.930,
            "road_name": None,
            "tree_score": 0.0,
            "hazard_score": 0.0,
            "dog_friendly_score": 0.3,
        },
    ]
    path = tmp_path / "scored_edges.json"
    path.write_text(json.dumps(edges), encoding="utf-8")
    return path


class TestImportTreeSegments:
    def test_imports_csv_rows(self) -> None:
        session = _make_session()
        import_tree_segments(session, _tree_csv_path(), encoding="cp949")
        count = session.query(TreeSegmentOrm).count()
        assert count == 8

    def test_idempotent(self) -> None:
        session = _make_session()
        import_tree_segments(session, _tree_csv_path(), encoding="cp949")
        import_tree_segments(session, _tree_csv_path(), encoding="cp949")
        count = session.query(TreeSegmentOrm).count()
        assert count == 8


class TestImportHazardZones:
    def test_imports_seoul_only(self) -> None:
        session = _make_session()
        import_hazard_zones(session, _hazard_csv_path(), encoding="cp949")
        count = session.query(HazardZoneOrm).count()
        assert count == 7

    def test_idempotent(self) -> None:
        session = _make_session()
        import_hazard_zones(session, _hazard_csv_path(), encoding="cp949")
        import_hazard_zones(session, _hazard_csv_path(), encoding="cp949")
        count = session.query(HazardZoneOrm).count()
        assert count == 7


class TestImportScoredEdges:
    def test_imports_edges_and_nodes(self, tmp_path: Path) -> None:
        session = _make_session()
        json_path = _make_scored_edges_json(tmp_path)
        import_scored_edges(session, json_path)

        node_count = session.query(RouteNodeOrm).count()
        edge_count = session.query(RouteEdgeOrm).count()
        assert node_count == 3
        assert edge_count == 2

    def test_scores_are_stored(self, tmp_path: Path) -> None:
        session = _make_session()
        json_path = _make_scored_edges_json(tmp_path)
        import_scored_edges(session, json_path)

        edge = session.query(RouteEdgeOrm).filter(
            RouteEdgeOrm.road_name == "여의대로"
        ).one()
        assert edge.tree_score == 0.8
        assert edge.hazard_score == 0.2
        assert edge.dog_friendly_score == 0.86

    def test_osm_id_stored_on_nodes(self, tmp_path: Path) -> None:
        session = _make_session()
        json_path = _make_scored_edges_json(tmp_path)
        import_scored_edges(session, json_path)

        node = session.query(RouteNodeOrm).filter(
            RouteNodeOrm.osm_id == "100"
        ).one()
        assert abs(node.latitude - 37.527) < 0.001

    def test_idempotent(self, tmp_path: Path) -> None:
        session = _make_session()
        json_path = _make_scored_edges_json(tmp_path)
        import_scored_edges(session, json_path)
        import_scored_edges(session, json_path)
        assert session.query(RouteEdgeOrm).count() == 2
