"""PgRouteGraphRepository 단위 테스트 — SQLite in-memory DB."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import gildle.adapter.outbound.orm.route_edge_orm  # noqa: F401
import gildle.adapter.outbound.orm.route_node_orm  # noqa: F401
from gildle.adapter.outbound.orm.base import GildleBase
from gildle.adapter.outbound.orm.route_edge_orm import RouteEdgeOrm
from gildle.adapter.outbound.orm.route_node_orm import RouteNodeOrm
from gildle.adapter.outbound.pg.route_graph_pg_repository import (
    PgRouteGraphRepository,
)


def _make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    GildleBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    return factory()


def _seed_graph(session: Session) -> None:
    """3 nodes, 2 edges — A→B→C 선형 경로."""
    n1 = RouteNodeOrm(latitude=37.526, longitude=126.924, node_type="osm", osm_id="100")
    n2 = RouteNodeOrm(latitude=37.528, longitude=126.928, node_type="osm", osm_id="200")
    n3 = RouteNodeOrm(latitude=37.530, longitude=126.932, node_type="osm", osm_id="300")
    session.add_all([n1, n2, n3])
    session.flush()

    e1 = RouteEdgeOrm(
        from_node_id=n1.id,
        to_node_id=n2.id,
        base_distance_m=150.0,
        road_name="여의대로",
        tree_score=0.8,
        hazard_score=0.2,
        dog_friendly_score=0.86,
    )
    e2 = RouteEdgeOrm(
        from_node_id=n2.id,
        to_node_id=n3.id,
        base_distance_m=200.0,
        road_name=None,
        tree_score=0.0,
        hazard_score=0.0,
        dog_friendly_score=0.3,
    )
    session.add_all([e1, e2])
    session.commit()


class TestLoadEdges:
    def test_empty_table_returns_empty_list(self) -> None:
        session = _make_session()
        repo = PgRouteGraphRepository(session_factory=lambda: session)
        assert repo.load_edges() == []

    def test_loads_edges_with_osm_id_as_node_key(self) -> None:
        session = _make_session()
        _seed_graph(session)

        repo = PgRouteGraphRepository(session_factory=lambda: session)
        edges = repo.load_edges()

        assert len(edges) == 2
        e = edges[0]
        assert e.from_node == "100"
        assert e.to_node == "200"
        assert e.base_distance_m == 150.0
        assert e.road_name == "여의대로"

    def test_scores_are_loaded(self) -> None:
        session = _make_session()
        _seed_graph(session)

        repo = PgRouteGraphRepository(session_factory=lambda: session)
        edges = repo.load_edges()

        scored = [e for e in edges if e.road_name == "여의대로"]
        assert len(scored) == 1
        assert scored[0].tree_score == 0.8
        assert scored[0].hazard_score == 0.2
        assert scored[0].dog_friendly_score == 0.86

    def test_midpoint_is_average_of_nodes(self) -> None:
        session = _make_session()
        _seed_graph(session)

        repo = PgRouteGraphRepository(session_factory=lambda: session)
        edges = repo.load_edges()

        e = edges[0]
        assert abs(e.midpoint.latitude - 37.527) < 0.001
        assert abs(e.midpoint.longitude - 126.926) < 0.001


class TestBuildGraphAndShortestPath:
    def test_build_graph_from_db(self) -> None:
        session = _make_session()
        _seed_graph(session)

        repo = PgRouteGraphRepository(session_factory=lambda: session)
        edges = repo.load_edges()
        graph = repo.build_graph(edges)

        assert graph.number_of_nodes() == 3
        assert graph.number_of_edges() == 2

    def test_shortest_path(self) -> None:
        session = _make_session()
        _seed_graph(session)

        repo = PgRouteGraphRepository(session_factory=lambda: session)
        edges = repo.load_edges()
        graph = repo.build_graph(edges)

        path = repo.find_shortest_path(graph, "100", "300", weight_fn=lambda e: e.base_distance_m)
        assert path == ["100", "200", "300"]

    def test_no_path_returns_empty(self) -> None:
        session = _make_session()
        _seed_graph(session)

        repo = PgRouteGraphRepository(session_factory=lambda: session)
        edges = repo.load_edges()
        graph = repo.build_graph(edges)

        path = repo.find_shortest_path(graph, "100", "999", weight_fn=lambda e: e.base_distance_m)
        assert path == []
