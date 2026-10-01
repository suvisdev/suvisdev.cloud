"""scored_edges.json에 도로 종류(highway)와 보도 유무(sidewalk)를 싣는 배치(2026-10-01).

    PYTHONPATH=apps python -m gildle.scripts.enrich_road_kind [--dry-run]

배경: osmnx `network_type="walk"` 그래프는 차도 중심선을 보도와 같은 비용으로 담고 있어
강남대로 한가운데를 지나는 경로가 나왔다(2026-09-30 제보). 기존 scored_edges.json에는
도로 종류가 없어 라우터가 구분하지 못했다. 여기서 두 값을 채우면 `road_penalty`가 쓴다.

- `highway`: 원본 GraphML(`graph_cache/seoul.graphml`)의 간선 `highway` 태그(목록이면 첫 값).
- `sidewalk`: 차도 간선(primary·secondary·tertiary·trunk·busway·*_link)의 **15m 버퍼 안에**
  보도형 간선(footway·path·pedestrian·steps·corridor)이 차도 길이의 절반 이상 들어 있으면 참.
  횡단보도처럼 차도를 가로지르기만 하는 짧은 보도는 절반을 못 채워 거짓이 된다.

출력은 임시 파일에 쓴 뒤 교체한다 — 서빙 파드는 hostPath mtime 캐시로 곧바로 새 값을 읽는다.
원본은 graph_cache/에 백업한다. 멱등(값을 다시 계산해 덮어쓸 뿐).
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import shutil
import time
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from shapely.geometry import LineString
from shapely.strtree import STRtree

from gildle.domain.services.road_penalty import is_car_road

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_LAT0 = 37.55  # 등장방형 투영 기준 위도(서울) — 수십 m 판정엔 충분

SIDEWALK_KINDS = frozenset({"footway", "path", "pedestrian", "steps", "corridor"})
_SIDEWALK_NEAR_M = 15.0
_SIDEWALK_MIN_COVER = 0.5  # 버퍼 안 보도 길이 ≥ 차도 길이 × 0.5


def _xy(lat: float, lng: float) -> tuple[float, float]:
    return (lng * 111_320.0 * math.cos(math.radians(_LAT0)), lat * 110_540.0)


def _line(rec: dict[str, Any]) -> LineString:
    return LineString([_xy(rec["from_lat"], rec["from_lng"]), _xy(rec["to_lat"], rec["to_lng"])])


def _pair(a: str, b: str) -> str:
    return f"{min(a, b)}|{max(a, b)}"


def load_highway_tags(graphml: Path) -> dict[str, str | None]:
    """GraphML의 간선별 highway 태그 — 키는 '작은노드|큰노드'(scored_edges와 같은 무향 쌍)."""
    import osmnx as ox

    graph = ox.load_graphml(graphml)
    tags: dict[str, str | None] = {}
    for u, v, data in graph.edges(data=True):
        key = _pair(str(u), str(v))
        if key in tags:
            continue
        raw = data.get("highway")
        if isinstance(raw, list):
            raw = raw[0] if raw else None
        tags[key] = str(raw) if raw is not None else None
    return tags


def sidewalk_flags(records: list[dict[str, Any]]) -> list[bool]:
    """차도 간선마다 옆에 보도형 간선이 그려져 있는지(순수 기하 — 테스트 가능)."""
    walk_lines = [_line(r) for r in records if r.get("highway") in SIDEWALK_KINDS]
    if not walk_lines:
        return [False] * len(records)
    tree = STRtree(walk_lines)
    flags: list[bool] = []
    for r in records:
        if not is_car_road(r.get("highway")):
            flags.append(False)
            continue
        line = _line(r)
        buf = line.buffer(_SIDEWALK_NEAR_M)
        covered = sum(walk_lines[i].intersection(buf).length for i in tree.query(buf))
        flags.append(covered >= _SIDEWALK_MIN_COVER * max(line.length, 1.0))
    return flags


def enrich(records: list[dict[str, Any]], tags: dict[str, str | None] | None) -> dict[str, Any]:
    if tags is not None:
        missing = 0
        for r in records:
            hw = tags.get(_pair(str(r["from_node"]), str(r["to_node"])))
            if hw is None:
                missing += 1
            r["highway"] = hw
    else:
        missing = sum(1 for r in records if r.get("highway") is None)
    flags = sidewalk_flags(records)
    for r, f in zip(records, flags, strict=True):
        r["sidewalk"] = f
    car = Counter(r["highway"] for r in records if is_car_road(r.get("highway")))
    car_sw = Counter(r["highway"] for r in records if r["sidewalk"])
    return {
        "edges": len(records),
        "highway_missing": missing,
        "car_edges": sum(car.values()),
        "car_with_sidewalk": sum(car_sw.values()),
        "by_kind": {k: f"{car_sw[k]}/{car[k]}" for k in sorted(car)},
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edges", type=Path, default=_DATA_DIR / "scored_edges.json")
    ap.add_argument(
        "--graphml",
        type=Path,
        default=_DATA_DIR / "graph_cache" / "seoul.graphml",
        help="highway 태그 원본. 없으면 기존 highway 값으로 sidewalk만 다시 계산",
    )
    ap.add_argument("--dry-run", action="store_true", help="통계만 출력하고 파일은 건드리지 않는다")
    args = ap.parse_args()

    t0 = time.perf_counter()
    records = json.loads(args.edges.read_text(encoding="utf-8"))
    tags = load_highway_tags(args.graphml) if args.graphml.exists() else None
    if tags is None:
        logger.warning("GraphML 없음: %s — highway는 기존 값 사용", args.graphml)
    stats = enrich(records, tags)
    stats["seconds"] = round(time.perf_counter() - t0, 1)
    print(json.dumps(stats, ensure_ascii=False))
    if args.dry_run:
        return

    backup_dir = _DATA_DIR / "graph_cache"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"scored_edges.before-road-kind-{date.today():%Y%m%d}.json"
    if not backup.exists():
        shutil.copy2(args.edges, backup)
        logger.info("백업: %s", backup)
    tmp = args.edges.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, args.edges)
    logger.info("저장: %s", args.edges)


if __name__ == "__main__":
    main()
