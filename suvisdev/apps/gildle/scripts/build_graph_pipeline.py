"""OSM → RouteEdge → 점수 산정 → scored_edges JSON 전체 파이프라인.

독립 실행: python -m gildle.scripts.build_graph_pipeline
단계: GraphML 로드 → edge 변환 → 점수 산정 → scored_edges.json 저장.
"""

from __future__ import annotations

import logging
from pathlib import Path

from gildle.adapter.outbound.graph.osm_walk_graph_adapter import OsmWalkGraphAdapter
from gildle.adapter.outbound.repositories.csv_tree_segment_repository import (
    CsvTreeSegmentRepository,
)
from gildle.adapter.outbound.repositories.traffic_authority_hazard_zone_repository import (
    TrafficAuthorityHazardZoneRepository,
)
from gildle.domain.value_objects.route_edge import RouteEdge
from gildle.scripts.compute_edge_scores import (
    EdgeScoreCalculator,
    save_scored_edges,
)

logger = logging.getLogger(__name__)


def run_pipeline(
    graphml_path: Path,
    tree_csv: Path,
    hazard_csv: Path,
    output_path: Path,
    csv_encoding: str = "cp949",
) -> list[RouteEdge]:
    adapter = OsmWalkGraphAdapter()
    edges = adapter.load_from_graphml(graphml_path)
    logger.info("edges: %d", len(edges))

    segments = CsvTreeSegmentRepository(csv_path=tree_csv, encoding=csv_encoding).find_all()
    hazards = TrafficAuthorityHazardZoneRepository(
        csv_path=hazard_csv, encoding=csv_encoding
    ).find_all()
    logger.info("segments: %d  hazards: %d", len(segments), len(hazards))

    calc = EdgeScoreCalculator()
    scored = calc.score_edges(edges, segments, hazards)

    nonzero_tree = sum(1 for e in scored if e.tree_score > 0)
    nonzero_hazard = sum(1 for e in scored if e.hazard_score > 0)
    logger.info("tree_score>0: %d  hazard_score>0: %d", nonzero_tree, nonzero_hazard)

    save_scored_edges(scored, output_path)
    logger.info("저장: %s (%d edges)", output_path, len(scored))

    return scored


def main() -> None:
    import os

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    data_dir = Path(__file__).resolve().parent.parent / "data"
    cache_dir = Path(os.getenv("GILDLE_GRAPH_CACHE_DIR", str(data_dir / "graph_cache")))
    graphml = cache_dir / "yeongdeungpo_yeouido.graphml"

    if not graphml.exists():
        logger.error("GraphML 없음: %s — 먼저 download_osm_graph를 실행하세요.", graphml)
        raise SystemExit(1)

    tree_csv = Path(os.getenv("GILDLE_TREE_CSV", str(data_dir / "yeongdeungpo_tree_segments.csv")))
    hazard_csv = Path(os.getenv("GILDLE_HAZARD_CSV", str(data_dir / "icing_accident_zones.csv")))
    encoding = os.getenv("GILDLE_CSV_ENCODING", "cp949")
    output = Path(os.getenv("GILDLE_SCORED_EDGES", str(data_dir / "scored_edges.json")))

    run_pipeline(
        graphml_path=graphml,
        tree_csv=tree_csv,
        hazard_csv=hazard_csv,
        output_path=output,
        csv_encoding=encoding,
    )


if __name__ == "__main__":
    main()
