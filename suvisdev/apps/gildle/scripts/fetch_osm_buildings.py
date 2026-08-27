"""서울 건물 풋프린트+높이 Overpass 수집 배치.

사용법(노트북, 네트워크 필요 — 전체 약 20~40분):
    python apps/gildle/scripts/fetch_osm_buildings.py            # 서울 전역
    python apps/gildle/scripts/fetch_osm_buildings.py \
        --bbox 37.51 126.90 37.54 126.95                         # 부분 테스트

타일 단위로 Overpass에 나눠 질의하고(타임아웃 회피), 결과를 하나의 JSON으로
저장한다. 높이는 height 태그(m) → building:levels×3.0m → 기본 6.0m 순.
산출물: apps/gildle/data/seoul_buildings_osm.json (gitignore 대상)
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

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_SEOUL_BBOX = (37.42, 126.76, 37.70, 127.19)  # south, west, north, east
_TILE_STEP = 0.02
_LEVEL_HEIGHT_M = 3.0
_DEFAULT_HEIGHT_M = 6.0
_SLEEP_BETWEEN_TILES_S = 1.0
_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def resolve_height_m(tags: dict[str, str]) -> float:
    """height(m) → building:levels×3.0 → 기본 6.0 순으로 건물 높이를 정한다."""
    raw_height = tags.get("height", "")
    if raw_height:
        try:
            return float(raw_height.split()[0].removesuffix("m"))
        except ValueError:
            pass
    raw_levels = tags.get("building:levels", "")
    if raw_levels:
        try:
            return float(raw_levels) * _LEVEL_HEIGHT_M
        except ValueError:
            pass
    return _DEFAULT_HEIGHT_M


def make_tiles(
    south: float, west: float, north: float, east: float, step: float
) -> list[tuple[float, float, float, float]]:
    """bbox를 step 간격 타일로 나눈다(경계는 step 배수로 올림 커버)."""
    tiles: list[tuple[float, float, float, float]] = []
    lat = south
    while lat < north:
        lng = west
        while lng < east:
            tiles.append((lat, lng, lat + step, lng + step))
            lng += step
        lat += step
    return tiles


def fetch_tile(bbox: tuple[float, float, float, float]) -> list[dict[str, Any]]:
    """타일 하나의 building way를 geometry 포함으로 받아온다."""
    s, w, n, e = bbox
    query = f'[out:json][timeout:90];way["building"]({s},{w},{n},{e});out tags geom;'
    res = requests.post(
        _OVERPASS_URL,
        data={"data": query},
        timeout=120,
        # 기본 python-requests UA는 Overpass가 406으로 거부한다(실측 2026-08-27).
        headers={"User-Agent": "gildle-shade-batch/1.0 (suvisdev.cloud)"},
    )
    res.raise_for_status()
    buildings: list[dict[str, Any]] = []
    for el in res.json().get("elements", []):
        geometry = el.get("geometry") or []
        if len(geometry) < 3:
            continue
        outline = [[p["lat"], p["lon"]] for p in geometry]
        buildings.append({"outline": outline, "height_m": resolve_height_m(el.get("tags", {}))})
    return buildings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bbox", nargs=4, type=float, default=None, metavar=("SOUTH", "WEST", "NORTH", "EAST")
    )
    parser.add_argument("--out", default=str(_DATA_DIR / "seoul_buildings_osm.json"))
    args = parser.parse_args()

    bbox = tuple(args.bbox) if args.bbox else _SEOUL_BBOX
    tiles = make_tiles(*bbox, step=_TILE_STEP)
    logger.info("타일 %d개 수집 시작 bbox=%s", len(tiles), bbox)

    all_buildings: list[dict[str, Any]] = []
    for i, tile in enumerate(tiles, 1):
        try:
            got = fetch_tile(tile)
        except requests.RequestException as exc:
            logger.warning("타일 %d/%d 실패(건너뜀): %s", i, len(tiles), exc)
            continue
        all_buildings.extend(got)
        logger.info("타일 %d/%d — +%d (누계 %d)", i, len(tiles), len(got), len(all_buildings))
        time.sleep(_SLEEP_BETWEEN_TILES_S)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(all_buildings, ensure_ascii=False), encoding="utf-8")
    logger.info("저장 완료: %s (건물 %d동)", out_path, len(all_buildings))


if __name__ == "__main__":
    main()
