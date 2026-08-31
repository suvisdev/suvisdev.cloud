from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from gildle.adapter.outbound.geocoding.kakao_geocoding_adapter import (
    KakaoGeocodingAdapter,
)
from gildle.adapter.outbound.graph.networkx_route_graph_adapter import (
    NetworkXRouteGraphAdapter,
)
from gildle.adapter.outbound.graph.osm_walk_graph_adapter import OsmWalkGraphAdapter
from gildle.adapter.outbound.graph.sample_walk_graph_source import SampleWalkGraphSource
from gildle.adapter.outbound.repositories.csv_tree_segment_repository import (
    CsvTreeSegmentRepository,
)
from gildle.adapter.outbound.repositories.traffic_authority_hazard_zone_repository import (
    TrafficAuthorityHazardZoneRepository,
)
from gildle.app.ports.input.calculate_route_use_case import (
    CalculateDogFriendlyRouteUseCase,
)
from gildle.app.ports.input.get_map_data_use_case import (
    GetMapVisualizationDataUseCase,
)
from gildle.app.ports.input.import_tree_segment_use_case import ImportTreeSegmentUseCase
from gildle.app.ports.output.walk_graph_port import WalkGraphPort
from gildle.app.use_cases.calculate_route_interactor import (
    CalculateDogFriendlyRouteInteractor,
)
from gildle.app.use_cases.get_map_data_interactor import (
    GetMapVisualizationDataInteractor,
)
from gildle.app.use_cases.import_tree_segment_interactor import (
    ImportTreeSegmentInteractor,
)
from gildle.domain.services.route_weight_calculator import RouteWeightCalculator

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _db_mode() -> str:
    return os.getenv("GILDLE_DB_MODE", "csv")


def _tree_csv_path() -> Path:
    return Path(os.getenv("GILDLE_TREE_CSV", str(_DATA_DIR / "sample_tree_segments.csv")))


def _hazard_csv_path() -> Path:
    return Path(os.getenv("GILDLE_HAZARD_CSV", str(_DATA_DIR / "sample_hazard_zones.csv")))


def _walk_graph_path() -> Path:
    return Path(os.getenv("GILDLE_WALK_GRAPH", str(_DATA_DIR / "sample_walk_graph.json")))


def _csv_encoding() -> str:
    return os.getenv("GILDLE_CSV_ENCODING", "utf-8-sig")


def get_walk_graph_source() -> SampleWalkGraphSource:
    return SampleWalkGraphSource(json_path=_walk_graph_path())


def _graph_cache_dir() -> Path:
    return Path(os.getenv("GILDLE_GRAPH_CACHE_DIR", str(_DATA_DIR / "graph_cache")))


def get_walk_graph_port() -> WalkGraphPort:
    source = os.getenv("GILDLE_WALK_GRAPH_SOURCE", "sample")
    if source == "osm":
        return OsmWalkGraphAdapter(cache_dir=_graph_cache_dir())
    return OsmWalkGraphAdapter(cache_dir=None)


def _get_gildle_session_factory() -> Any:
    """gildle 전용 sync SQLAlchemy 세션 팩토리. postgres 모드에서만 호출."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgresql://") and "+psycopg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=300)
    return sessionmaker(bind=engine)


def get_calculate_route_use_case() -> CalculateDogFriendlyRouteUseCase:
    if _db_mode() == "postgres":
        from gildle.adapter.outbound.pg.hazard_zone_pg_repository import (
            PgHazardZoneRepository,
        )
        from gildle.adapter.outbound.pg.route_graph_pg_repository import (
            PgRouteGraphRepository,
        )
        from gildle.adapter.outbound.pg.tree_segment_pg_repository import (
            PgTreeSegmentRepository,
        )

        factory = _get_gildle_session_factory()
        return CalculateDogFriendlyRouteInteractor(
            tree_repository=PgTreeSegmentRepository(session_factory=factory),
            hazard_repository=PgHazardZoneRepository(session_factory=factory),
            route_graph=PgRouteGraphRepository(session_factory=factory),
            weight_calculator=RouteWeightCalculator(),
        )

    encoding = _csv_encoding()
    return CalculateDogFriendlyRouteInteractor(
        tree_repository=CsvTreeSegmentRepository(csv_path=_tree_csv_path(), encoding=encoding),
        hazard_repository=TrafficAuthorityHazardZoneRepository(
            csv_path=_hazard_csv_path(), encoding=encoding
        ),
        route_graph=NetworkXRouteGraphAdapter(),
        weight_calculator=RouteWeightCalculator(),
    )


def get_map_data_use_case() -> GetMapVisualizationDataUseCase:
    if _db_mode() == "postgres":
        from gildle.adapter.outbound.pg.hazard_zone_pg_repository import (
            PgHazardZoneRepository,
        )
        from gildle.adapter.outbound.pg.tree_segment_pg_repository import (
            PgTreeSegmentRepository,
        )

        factory = _get_gildle_session_factory()
        return GetMapVisualizationDataInteractor(
            tree_repository=PgTreeSegmentRepository(session_factory=factory),
            hazard_repository=PgHazardZoneRepository(session_factory=factory),
        )

    encoding = _csv_encoding()
    return GetMapVisualizationDataInteractor(
        tree_repository=CsvTreeSegmentRepository(csv_path=_tree_csv_path(), encoding=encoding),
        hazard_repository=TrafficAuthorityHazardZoneRepository(
            csv_path=_hazard_csv_path(), encoding=encoding
        ),
    )


def get_import_tree_segment_use_case() -> ImportTreeSegmentUseCase:
    return ImportTreeSegmentInteractor(geocoder=KakaoGeocodingAdapter())
