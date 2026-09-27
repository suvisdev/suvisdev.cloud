"""scored_edges.json의 tree_score·dog_friendly_score를 OSM 수관 데이터로 보강하는 배치.

    PYTHONPATH=apps python -m gildle.scripts.enrich_tree_scores [--dry-run]

배경(2026-09-27): tree_score>0 간선이 4.4%뿐이었다 — 원천이 자치구 가로수 CSV 12행 +
OSM 나무 점 6,851개(중점 80m 매칭)라서 산길·공원길처럼 나무는 많은데 "가로수 점"이
없는 곳이 전부 0이었다. 여기서는 간선을 **선분**으로 보고 네 가지 원천을 합친다.

| 원천(`seoul_canopy_osm.json` · `seoul_trees_osm.json`) | 판정 | 점수 |
|---|---|---|
| natural=wood · landuse=forest 폴리곤 | 선분 중점이 안에 있거나 선분이 폴리곤과 10m 이내 | 1.0 |
| leisure=park 폴리곤 | 같은 판정 | 0.6 (잔디·광장이 섞여 숲보다 낮게) |
| natural=tree_row 선 | 선분에서 15m 이내 | 0.9 |
| natural=tree 점 | 선분에서 25m 이내 개수 / (길이÷12m) | 0~1 (12m 간격이면 1.0) |

새 tree_score = max(기존, 위 넷). 기존 값을 하한으로 두므로 여러 번 돌려도 같다(멱등).
dog_friendly_score는 compute_edge_scores와 같은 식(tree×0.7+0.3)에 공원 150m 이내
+0.4(08-25 규칙 유지)다. 출력은 임시 파일에 쓴 뒤 교체한다 — 서빙 파드는 hostPath
mtime 캐시로 곧바로 새 값을 읽는다. 원본은 graph_cache/에 백업한다.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import shutil
import time
from datetime import date
from pathlib import Path
from typing import Any

from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_LAT0 = 37.55  # 등장방형 투영 기준 위도(서울) — 수십 m 판정엔 충분

_WOOD_SCORE = 1.0
_PARK_SCORE = 0.6
_TREE_ROW_SCORE = 0.9
_POLYGON_NEAR_M = 10.0
_TREE_ROW_NEAR_M = 15.0
_TREE_POINT_NEAR_M = 25.0
_TREE_SPACING_M = 12.0  # 이 간격으로 나무가 있으면 만점
_PARK_DOG_BOOST_M = 150.0
_DOG_FRIENDLY_TREE_WEIGHT = 0.7
_DOG_FRIENDLY_BASE = 0.3
_DOG_PARK_BOOST = 0.4


def _xy(lat: float, lng: float) -> tuple[float, float]:
    return (lng * 111_320.0 * math.cos(math.radians(_LAT0)), lat * 110_540.0)


def _edge_line(rec: dict[str, Any]) -> LineString:
    if "from_lat" in rec and "to_lat" in rec:
        a = _xy(rec["from_lat"], rec["from_lng"])
        b = _xy(rec["to_lat"], rec["to_lng"])
        if a != b:
            return LineString([a, b])
    x, y = _xy(rec["midpoint_lat"], rec["midpoint_lng"])
    return LineString([(x, y), (x + 0.01, y)])


def load_canopy(path: Path) -> tuple[list[Polygon], list[str], list[LineString]]:
    """수관 파일 → (폴리곤, 종류, 나무열 선). 자기교차 등 무효 폴리곤은 buffer(0)로 고친다."""
    polys: list[Polygon] = []
    kinds: list[str] = []
    rows: list[LineString] = []
    for f in json.loads(path.read_text(encoding="utf-8")):
        if "line" in f:
            pts = [_xy(lat, lng) for lat, lng in f["line"]]
            if len(pts) >= 2:
                rows.append(LineString(pts))
            continue
        ring = [_xy(lat, lng) for lat, lng in f["outline"]]
        if len(ring) < 4:
            continue
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            continue
        polys.append(poly)
        kinds.append(f["kind"])
    return polys, kinds, rows


def load_tree_points(path: Path) -> list[Point]:
    pts: list[Point] = []
    for el in json.loads(path.read_text(encoding="utf-8")):
        if el.get("type") == "node" and "lat" in el:
            pts.append(Point(_xy(el["lat"], el["lon"])))
        elif "center" in el and el.get("type") == "way":
            # tree_row way는 center만 있는 옛 파일 형식 — 선은 canopy 파일이 담당, 점으로는 안 센다.
            continue
    return pts


class CanopyScorer:
    """간선 선분 하나의 수관 점수를 STRtree로 계산한다."""

    def __init__(
        self,
        polys: list[Polygon],
        kinds: list[str],
        rows: list[LineString],
        points: list[Point],
    ) -> None:
        self._polys = polys
        self._kinds = kinds
        self._poly_tree = STRtree(polys) if polys else None
        self._rows = rows
        self._row_tree = STRtree(rows) if rows else None
        self._points = points
        self._point_tree = STRtree(points) if points else None

    def score(self, line: LineString) -> tuple[float, bool]:
        """(수관 점수, 공원 150m 이내 여부)."""
        best = 0.0
        near_park = False
        if self._poly_tree is not None:
            for i in self._poly_tree.query(line.buffer(_PARK_DOG_BOOST_M)):
                poly = self._polys[i]
                d = poly.distance(line)
                kind = self._kinds[i]
                if kind == "park" and d <= _PARK_DOG_BOOST_M:
                    near_park = True
                if d <= _POLYGON_NEAR_M:
                    best = max(best, _PARK_SCORE if kind == "park" else _WOOD_SCORE)
        if best < _TREE_ROW_SCORE and self._row_tree is not None:
            for i in self._row_tree.query(line.buffer(_TREE_ROW_NEAR_M)):
                if self._rows[i].distance(line) <= _TREE_ROW_NEAR_M:
                    best = max(best, _TREE_ROW_SCORE)
                    break
        if best < 1.0 and self._point_tree is not None:
            n = sum(
                1
                for i in self._point_tree.query(line.buffer(_TREE_POINT_NEAR_M))
                if self._points[i].distance(line) <= _TREE_POINT_NEAR_M
            )
            if n:
                expected = max(2.0, line.length / _TREE_SPACING_M)
                best = max(best, min(1.0, n / expected))
        return best, near_park


def enrich(records: list[dict[str, Any]], scorer: CanopyScorer) -> dict[str, Any]:
    """records를 제자리에서 갱신하고 전후 통계를 돌려준다."""
    before_pos = sum(1 for r in records if r.get("tree_score", 0) > 0)
    before_dog = sum(1 for r in records if r.get("dog_friendly_score", 0) > 0.3)
    changed = 0
    for r in records:
        canopy, near_park = scorer.score(_edge_line(r))
        old = float(r.get("tree_score", 0.0))
        new = round(max(old, canopy), 6)
        dog = min(1.0, new * _DOG_FRIENDLY_TREE_WEIGHT + _DOG_FRIENDLY_BASE)
        if near_park:
            dog = min(1.0, dog + _DOG_PARK_BOOST)
        dog = round(dog, 6)
        if new != old or dog != r.get("dog_friendly_score"):
            changed += 1
        r["tree_score"] = new
        r["dog_friendly_score"] = dog
    n = len(records)
    after_pos = sum(1 for r in records if r["tree_score"] > 0)
    return {
        "edges": n,
        "tree_positive_before": before_pos,
        "tree_positive_after": after_pos,
        "tree_positive_ratio_before": round(before_pos / n, 4) if n else 0,
        "tree_positive_ratio_after": round(after_pos / n, 4) if n else 0,
        "tree_ge_0_5_after": sum(1 for r in records if r["tree_score"] >= 0.5),
        "dog_gt_0_3_before": before_dog,
        "dog_gt_0_3_after": sum(1 for r in records if r["dog_friendly_score"] > 0.3),
        "changed": changed,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edges", type=Path, default=_DATA_DIR / "scored_edges.json")
    ap.add_argument("--canopy", type=Path, default=_DATA_DIR / "seoul_canopy_osm.json")
    ap.add_argument("--trees", type=Path, default=_DATA_DIR / "seoul_trees_osm.json")
    ap.add_argument("--dry-run", action="store_true", help="통계만 출력하고 파일은 건드리지 않는다")
    args = ap.parse_args()

    t0 = time.perf_counter()
    polys, kinds, rows = load_canopy(args.canopy)
    points = load_tree_points(args.trees) if args.trees.exists() else []
    logger.info("수관 폴리곤 %d · 나무열 %d · 나무 점 %d", len(polys), len(rows), len(points))
    records = json.loads(args.edges.read_text(encoding="utf-8"))
    stats = enrich(records, CanopyScorer(polys, kinds, rows, points))
    stats["seconds"] = round(time.perf_counter() - t0, 1)
    print(json.dumps(stats, ensure_ascii=False))
    if args.dry_run:
        return

    backup_dir = _DATA_DIR / "graph_cache"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"scored_edges.before-tree-enrich-{date.today():%Y%m%d}.json"
    if not backup.exists():
        shutil.copy2(args.edges, backup)
        logger.info("백업: %s", backup)
    tmp = args.edges.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, args.edges)
    logger.info("저장: %s", args.edges)


if __name__ == "__main__":
    main()
