"""서울 수관(樹冠) 폴리곤 Overpass 수집 배치 — 숲·산림·공원.

    PYTHONPATH=apps python -m gildle.scripts.fetch_osm_canopy

`natural=wood` · `landuse=forest` · `leisure=park`의 way·relation을 geometry 포함으로
받아 폴리곤으로, `natural=tree_row`(가로수 열)는 선(line)으로 `data/seoul_canopy_osm.json`에
저장한다(`enrich_tree_scores.py`의 입력). `seoul_trees_osm.json`의 tree_row way는
center만 있어 선으로 못 쓴다.
relation은 role=outer이고 닫힌 멤버만 폴리곤으로 쓴다 — 여러 way로 이어진
바깥 고리(링 조립)는 건너뛰고 개수만 로그에 남긴다(서울에선 소수).
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# fetch_osm_buildings와 같은 미러·백오프 정책(공용 Overpass 과속 시 429 → 차단).
_OVERPASS_URLS = [
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
_SEOUL_BBOX = (37.42, 126.76, 37.70, 127.19)  # south, west, north, east
_KINDS = {
    "wood": '["natural"="wood"]',
    "forest": '["landuse"="forest"]',
    "park": '["leisure"="park"]',
    "tree_row": '["natural"="tree_row"]',
}
_LINE_KINDS = frozenset({"tree_row"})
_SLEEP_BETWEEN_QUERIES_S = 5.0
_RETRY_BACKOFFS_S = [15.0, 60.0, 180.0]
_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _closed(ring: list[list[float]]) -> bool:
    return len(ring) >= 4 and ring[0] == ring[-1]


def polygons_from_elements(
    kind: str, elements: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], int]:
    """Overpass `out geom` 결과 → {kind, id, outline|line} 목록. 두 번째 값은 건너뛴 열린 고리 수.
    선 종류(tree_row)는 점 2개 이상이면 그대로 `line`으로 담는다."""
    out: list[dict[str, Any]] = []
    skipped = 0
    for el in elements:
        if el.get("type") == "way":
            ring = [[p["lat"], p["lon"]] for p in el.get("geometry") or []]
            if kind in _LINE_KINDS:
                if len(ring) >= 2:
                    out.append({"kind": kind, "id": f"w{el['id']}", "line": ring})
                else:
                    skipped += 1
            elif _closed(ring):
                out.append({"kind": kind, "id": f"w{el['id']}", "outline": ring})
            else:
                skipped += 1
        elif el.get("type") == "relation":
            for i, m in enumerate(el.get("members") or []):
                if m.get("type") != "way" or m.get("role") != "outer":
                    continue
                ring = [[p["lat"], p["lon"]] for p in m.get("geometry") or []]
                if _closed(ring):
                    out.append({"kind": kind, "id": f"r{el['id']}_{i}", "outline": ring})
                else:
                    skipped += 1
    return out, skipped


def fetch_kind(kind: str, bbox: tuple[float, float, float, float]) -> list[dict[str, Any]]:
    s, w, n, e = bbox
    selector = _KINDS[kind]
    query = (
        f"[out:json][timeout:180];"
        f"(way{selector}({s},{w},{n},{e});relation{selector}({s},{w},{n},{e}););"
        f"out geom;"
    )
    last_exc: requests.RequestException | None = None
    for attempt, backoff in enumerate([0.0, *_RETRY_BACKOFFS_S]):
        if backoff:
            logger.info("%s 재시도 %d — %.0f초 대기", kind, attempt, backoff)
            time.sleep(backoff)
        url = _OVERPASS_URLS[attempt % len(_OVERPASS_URLS)]
        try:
            res = requests.post(
                url,
                data={"data": query},
                timeout=240,
                headers={"User-Agent": "gildle-canopy-batch/1.0 (suvisdev.cloud)"},
            )
            res.raise_for_status()
        except requests.RequestException as exc:
            last_exc = exc
            continue
        polys, skipped = polygons_from_elements(kind, res.json().get("elements", []))
        logger.info("%s: 폴리곤 %d개 (열린 고리 건너뜀 %d)", kind, len(polys), skipped)
        return polys
    raise last_exc  # type: ignore[misc]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bbox", nargs=4, type=float, default=None, metavar=("SOUTH", "WEST", "NORTH", "EAST")
    )
    parser.add_argument("--out", default=str(_DATA_DIR / "seoul_canopy_osm.json"))
    parser.add_argument(
        "--kinds",
        nargs="+",
        choices=sorted(_KINDS),
        default=None,
        help="일부 종류만 다시 받는다 — 기존 파일의 나머지 종류는 유지(멱등 갱신)",
    )
    args = parser.parse_args()
    bbox = tuple(args.bbox) if args.bbox else _SEOUL_BBOX
    kinds = args.kinds or list(_KINDS)

    out = Path(args.out)
    polygons: list[dict[str, Any]] = []
    if args.kinds and out.exists():
        polygons = [
            p for p in json.loads(out.read_text(encoding="utf-8")) if p["kind"] not in kinds
        ]
    for i, kind in enumerate(kinds):
        if i:
            time.sleep(_SLEEP_BETWEEN_QUERIES_S)
        polygons.extend(fetch_kind(kind, bbox))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(polygons, ensure_ascii=False), encoding="utf-8")
    logger.info("저장: %s (%d features)", out, len(polygons))


if __name__ == "__main__":
    main()
