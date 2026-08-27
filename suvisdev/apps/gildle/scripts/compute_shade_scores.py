"""엣지별×시간대별 그늘 비율 사전 계산 배치.

사용법(노트북 — 서울 전역 233k 엣지 × 13슬롯, 수십 분~수 시간, suvisdev/에서):
    PYTHONPATH=apps python -m gildle.scripts.compute_shade_scores
    PYTHONPATH=apps python -m gildle.scripts.compute_shade_scores --slots 8 12 16

원리: 대표일(2026-08-01) 각 정시 슬롯의 태양 고도·방위각으로 건물마다
그림자 폴리곤(풋프린트 ∪ 그림자 방향 평행이동본의 convex hull)을 만들고,
STRtree로 엣지 선분과 교차 길이 비율을 구한다. 나무 그늘은
min(1, 건물비율 + 0.6×tree_score)로 결합. 산출은 0~100 정수 퍼센트.
좌표는 등장방형 근사(중심 위도 기준)로 미터 평면에 투영한다.
산출물: apps/gildle/data/shade_scores.json (gitignore 대상)
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

from gildle.domain.services.sun_position import sun_altitude_azimuth

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_DATE = (2026, 8, 1)
_SLOTS = list(range(7, 20))  # 07..19 KST
_SEOUL_CENTER = (37.5665, 126.9780)
_TREE_SHADE_WEIGHT = 0.6
_MIN_SUN_ALT_DEG = 5.0  # 이보다 낮으면 전면 그늘(=100) 처리


def project_to_meters(lat: float, lng: float, lat0: float, lng0: float) -> tuple[float, float]:
    """등장방형 근사 — (lat0, lng0) 원점 기준 미터 좌표."""
    x = (lng - lng0) * 111320.0 * math.cos(math.radians(lat0))
    y = (lat - lat0) * 110540.0
    return x, y


def _shadow_polygon(
    outline_m: list[tuple[float, float]],
    height_m: float,
    sun_alt_deg: float,
    sun_az_deg: float,
) -> Polygon:
    length = height_m / math.tan(math.radians(sun_alt_deg))
    # 그림자는 태양 반대 방향: 방위각 az(북0 시계) 태양 → 그림자 벡터 az+180.
    az_rad = math.radians((sun_az_deg + 180.0) % 360.0)
    dx = length * math.sin(az_rad)
    dy = length * math.cos(az_rad)
    base = Polygon(outline_m)
    if not base.is_valid:
        base = base.buffer(0)
    moved = Polygon([(x + dx, y + dy) for x, y in base.exterior.coords])
    return unary_union([base, moved]).convex_hull


def compute_slot_fractions(
    edges: list[dict[str, Any]],
    buildings: list[dict[str, Any]],
    sun_alt_deg: float,
    sun_az_deg: float,
) -> dict[str, int]:
    """한 슬롯의 태양 위치에서 엣지별 그늘 퍼센트(0~100)를 계산한다."""
    lat0, lng0 = _SEOUL_CENTER

    if sun_alt_deg <= _MIN_SUN_ALT_DEG:
        return {f"{e['from_node']}-{e['to_node']}": 100 for e in edges}

    shadows = [
        _shadow_polygon(
            [project_to_meters(p[0], p[1], lat0, lng0) for p in b["outline"]],
            b["height_m"],
            sun_alt_deg,
            sun_az_deg,
        )
        for b in buildings
    ]
    tree = STRtree(shadows) if shadows else None

    result: dict[str, int] = {}
    for e in edges:
        key = f"{e['from_node']}-{e['to_node']}"
        if "from_lat" not in e or "to_lat" not in e:
            result[key] = 0
            continue
        line = LineString(
            [
                project_to_meters(e["from_lat"], e["from_lng"], lat0, lng0),
                project_to_meters(e["to_lat"], e["to_lng"], lat0, lng0),
            ]
        )
        building_frac = 0.0
        if tree is not None and line.length > 0:
            shaded = 0.0
            for idx in tree.query(line):
                shaded += shadows[idx].intersection(line).length
            building_frac = min(1.0, shaded / line.length)
        shade = min(1.0, building_frac + _TREE_SHADE_WEIGHT * float(e.get("tree_score", 0)))
        result[key] = round(shade * 100)
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", default=str(_DATA_DIR / "scored_edges.json"))
    parser.add_argument("--buildings", default=str(_DATA_DIR / "seoul_buildings_osm.json"))
    parser.add_argument("--out", default=str(_DATA_DIR / "shade_scores.json"))
    parser.add_argument("--slots", nargs="*", type=int, default=_SLOTS)
    args = parser.parse_args()

    edges = json.loads(Path(args.edges).read_text(encoding="utf-8"))
    buildings = json.loads(Path(args.buildings).read_text(encoding="utf-8"))
    logger.info("엣지 %d, 건물 %d, 슬롯 %s", len(edges), len(buildings), args.slots)

    per_edge: dict[str, list[int]] = {}
    for slot in args.slots:
        kst = timezone(timedelta(hours=9))
        dt_utc = datetime(*_DATE, slot, 0, tzinfo=kst)  # KST — 함수가 UTC로 변환
        alt, az = sun_altitude_azimuth(*_SEOUL_CENTER, dt_utc)
        logger.info("슬롯 %02d시 — 고도 %.1f° 방위 %.1f°", slot, alt, az)
        fractions = compute_slot_fractions(edges, buildings, alt, az)
        for key, pct in fractions.items():
            per_edge.setdefault(key, []).append(pct)

    out = {"date": "2026-08-01", "slots": args.slots, "edges": per_edge}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    logger.info("저장 완료: %s (엣지 %d)", args.out, len(per_edge))


if __name__ == "__main__":
    main()
