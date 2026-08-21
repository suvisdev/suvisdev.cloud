"""OSM 보행 그래프 다운로드 — 영등포구 여의도 일대.

독립 실행: python -m gildle.scripts.download_osm_graph
osmnx 2.x로 보행 그래프를 다운로드해 GraphML로 캐시한다.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_CENTER = (37.528, 126.933)
_DEFAULT_DIST_M = 1500


def _ox() -> Any:
    return importlib.import_module("osmnx")


def download_walk_graph(
    center: tuple[float, float],
    dist_m: int,
    output_path: Path,
) -> Path:
    ox = _ox()
    graph = ox.graph_from_point(center, dist=dist_m, network_type="walk")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, filepath=output_path)
    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()
    logger.info("다운로드 완료: %d nodes, %d edges → %s", n_nodes, n_edges, output_path)
    return output_path


def main() -> None:
    import os

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    data_dir = Path(__file__).resolve().parent.parent / "data"
    cache_dir = Path(os.getenv("GILDLE_GRAPH_CACHE_DIR", str(data_dir / "graph_cache")))
    output = cache_dir / "yeongdeungpo_yeouido.graphml"

    lat = float(os.getenv("GILDLE_OSM_CENTER_LAT", str(_DEFAULT_CENTER[0])))
    lng = float(os.getenv("GILDLE_OSM_CENTER_LNG", str(_DEFAULT_CENTER[1])))
    dist = int(os.getenv("GILDLE_OSM_DIST_M", str(_DEFAULT_DIST_M)))

    logger.info("center=(%s, %s)  dist=%dm", lat, lng, dist)
    download_walk_graph(center=(lat, lng), dist_m=dist, output_path=output)


if __name__ == "__main__":
    main()
