from __future__ import annotations

import os
from pathlib import Path

from gildle.adapter.outbound.geocoding.kakao_geocoding_adapter import (
    KakaoGeocodingAdapter,
)
from gildle.adapter.outbound.graph.networkx_route_graph_adapter import (
    NetworkXRouteGraphAdapter,
)
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

# Composition Root: 구체 어댑터를 조립해 Use Case(입력 포트)를 돌려준다.
# main.py 외에는 이 모듈만 구체 어댑터를 안다 — 라우터는 입력 포트(ABC)에만 의존(DIP).
# Repository를 CSV → PostgreSQL로 바꿔도 여기 한 줄만 고치면 Use Case는 그대로다(OCP).

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _tree_csv_path() -> Path:
    return Path(os.getenv("GILDLE_TREE_CSV", str(_DATA_DIR / "sample_tree_segments.csv")))


def _hazard_csv_path() -> Path:
    return Path(
        os.getenv("GILDLE_HAZARD_CSV", str(_DATA_DIR / "sample_hazard_zones.csv"))
    )


def _walk_graph_path() -> Path:
    return Path(os.getenv("GILDLE_WALK_GRAPH", str(_DATA_DIR / "sample_walk_graph.json")))


def _csv_encoding() -> str:
    # 실제 data.go.kr 파일이 cp949/euc-kr이면 GILDLE_CSV_ENCODING로 지정한다.
    return os.getenv("GILDLE_CSV_ENCODING", "utf-8-sig")


def get_walk_graph_source() -> SampleWalkGraphSource:
    return SampleWalkGraphSource(json_path=_walk_graph_path())


def get_calculate_route_use_case() -> CalculateDogFriendlyRouteUseCase:
    encoding = _csv_encoding()
    return CalculateDogFriendlyRouteInteractor(
        tree_repository=CsvTreeSegmentRepository(
            csv_path=_tree_csv_path(), encoding=encoding
        ),
        hazard_repository=TrafficAuthorityHazardZoneRepository(
            csv_path=_hazard_csv_path(), encoding=encoding
        ),
        route_graph=NetworkXRouteGraphAdapter(),
        weight_calculator=RouteWeightCalculator(),
    )


def get_map_data_use_case() -> GetMapVisualizationDataUseCase:
    encoding = _csv_encoding()
    return GetMapVisualizationDataInteractor(
        tree_repository=CsvTreeSegmentRepository(
            csv_path=_tree_csv_path(), encoding=encoding
        ),
        hazard_repository=TrafficAuthorityHazardZoneRepository(
            csv_path=_hazard_csv_path(), encoding=encoding
        ),
    )


def get_import_tree_segment_use_case() -> ImportTreeSegmentUseCase:
    # 좌표가 이미 있는 표준데이터를 가정 → geocoding fallback은 선택적(여기선 사용 안 함).
    return ImportTreeSegmentInteractor(geocoder=KakaoGeocodingAdapter())
