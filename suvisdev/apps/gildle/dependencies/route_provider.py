from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from gildle.adapter.outbound.graph.dijkstra_route_graph_adapter import (
    AStarRouteGraphAdapter,
)
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
from gildle.app.ports.input.plan_loop_use_case import PlanLoopRouteUseCase
from gildle.app.ports.input.route_options_use_case import RouteOptionsUseCase
from gildle.app.ports.input.walk_plan_use_case import WalkPlanUseCase
from gildle.app.ports.output.pet_place_port import PetPlacePort
from gildle.app.use_cases.calculate_route_interactor import (
    CalculateDogFriendlyRouteInteractor,
)
from gildle.app.use_cases.get_map_data_interactor import (
    GetMapVisualizationDataInteractor,
)
from gildle.app.use_cases.plan_loop_interactor import PlanLoopRouteInteractor
from gildle.domain.services.route_weight_calculator import RouteWeightCalculator

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _db_mode() -> str:
    return os.getenv("GILDLE_DB_MODE", "csv")


def _tree_csv_path() -> Path:
    return Path(os.getenv("GILDLE_TREE_CSV", str(_DATA_DIR / "sample_tree_segments.csv")))


def _hazard_csv_path() -> Path:
    return Path(os.getenv("GILDLE_HAZARD_CSV", str(_DATA_DIR / "sample_hazard_zones.csv")))


def _csv_encoding() -> str:
    return os.getenv("GILDLE_CSV_ENCODING", "utf-8-sig")


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
        # 자체 A*(2026-09-22): 실데이터 200쌍에서 networkx와 경로 비용 불일치 0건 확인 후 교체.
        # 시간 의존 그늘(③)·제약 최단경로(④)·루프(⑤)가 이 구현체를 전제한다.
        route_graph=AStarRouteGraphAdapter(),
        weight_calculator=RouteWeightCalculator(),
    )


def get_plan_loop_use_case() -> PlanLoopRouteUseCase:
    encoding = _csv_encoding()
    return PlanLoopRouteInteractor(
        tree_repository=CsvTreeSegmentRepository(csv_path=_tree_csv_path(), encoding=encoding),
        hazard_repository=TrafficAuthorityHazardZoneRepository(
            csv_path=_hazard_csv_path(), encoding=encoding
        ),
        route_graph=AStarRouteGraphAdapter(),
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


@lru_cache(maxsize=1)
def _shared_pet_place_adapter() -> PetPlacePort:
    from gildle.adapter.outbound.http.kakao_pet_place_adapter import KakaoPetPlaceAdapter

    return KakaoPetPlaceAdapter()


def get_route_options_use_case() -> RouteOptionsUseCase:
    from gildle.app.use_cases.route_options_interactor import RouteOptionsInteractor

    return RouteOptionsInteractor(
        route=get_calculate_route_use_case(),
        places=_shared_pet_place_adapter(),
        loops=get_plan_loop_use_case(),
    )


@lru_cache(maxsize=1)
def _shared_walk_understanding() -> Any:
    from gildle.adapter.outbound.llm.exaone_walk_understanding_adapter import (
        ExaoneWalkUnderstandingAdapter,
    )

    return ExaoneWalkUnderstandingAdapter()


def get_walk_plan_use_case() -> WalkPlanUseCase:
    """자연어 산책 요청 → 7.8B 이해 + 규칙 검증 → 루프/경로 후보(2026-09-28)."""
    from gildle.app.use_cases.walk_plan_interactor import WalkPlanInteractor

    enabled = os.getenv("GILDLE_UNDERSTANDING", "llm") == "llm"
    return WalkPlanInteractor(
        options=get_route_options_use_case(),
        understanding=_shared_walk_understanding() if enabled else None,
    )
