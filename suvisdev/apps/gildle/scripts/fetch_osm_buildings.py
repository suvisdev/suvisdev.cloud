"""서울 건물 풋프린트+높이 Overpass 수집 배치.

사용법(노트북, 네트워크 필요 — 전체 약 20~40분, suvisdev/에서):
    PYTHONPATH=apps python -m gildle.scripts.fetch_osm_buildings   # 서울 전역
    PYTHONPATH=apps python -m gildle.scripts.fetch_osm_buildings \
        --bbox 37.51 126.90 37.54 126.95                           # 부분 테스트

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

# 공용 Overpass는 과속 시 429 → 연결 차단까지 간다(실측 2026-08-27, 1초
# 간격으로 53타일 만에 차단). 미러를 순환하고 지수 백오프로 재시도한다.
_OVERPASS_URLS = [
    # osm.fr이 이 회선에서 안정적(실측). kumi는 private.coffee 별칭이라 하나만.
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
_SEOUL_BBOX = (37.42, 126.76, 37.70, 127.19)  # south, west, north, east
_TILE_STEP = 0.02
_LEVEL_HEIGHT_M = 3.0
_DEFAULT_HEIGHT_M = 6.0
_SLEEP_BETWEEN_TILES_S = 3.0
_RETRY_BACKOFFS_S = [15.0, 60.0, 180.0]
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


def fetch_tile(bbox: tuple[float, float, float, float], tile_no: int) -> list[dict[str, Any]]:
    """타일 하나의 building way를 geometry 포함으로 받아온다.

    미러를 순환하며 429·연결 오류는 지수 백오프로 재시도한다.
    """
    s, w, n, e = bbox
    query = f'[out:json][timeout:90];way["building"]({s},{w},{n},{e});out tags geom;'
    last_exc: requests.RequestException | None = None
    for attempt, backoff in enumerate([0.0, *_RETRY_BACKOFFS_S]):
        if backoff:
            logger.info("타일 %d 재시도 %d — %.0f초 대기", tile_no, attempt, backoff)
            time.sleep(backoff)
        url = _OVERPASS_URLS[(tile_no + attempt) % len(_OVERPASS_URLS)]
        try:
            res = requests.post(
                url,
                data={"data": query},
                timeout=120,
                # 기본 python-requests UA는 Overpass가 406으로 거부(실측 2026-08-27).
                headers={"User-Agent": "gildle-shade-batch/1.0 (suvisdev.cloud)"},
            )
            res.raise_for_status()
        except requests.RequestException as exc:
            last_exc = exc
            continue
        buildings: list[dict[str, Any]] = []
        for el in res.json().get("elements", []):
            geometry = el.get("geometry") or []
            if len(geometry) < 3:
                continue
            outline = [[p["lat"], p["lon"]] for p in geometry]
            buildings.append({"outline": outline, "height_m": resolve_height_m(el.get("tags", {}))})
        return buildings
    raise last_exc  # type: ignore[misc]  # 첫 시도 전엔 도달 불가


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

    # 이어받기: 완료 타일 번호를 사이드카에 기록해 재실행 시 건너뛴다.
    out_path = Path(args.out)
    state_path = out_path.with_suffix(".state.json")
    all_buildings: list[dict[str, Any]] = []
    done_tiles: set[int] = set()
    if out_path.exists() and state_path.exists():
        all_buildings = json.loads(out_path.read_text(encoding="utf-8"))
        done_tiles = set(json.loads(state_path.read_text(encoding="utf-8")))
        logger.info("이어받기 — 완료 타일 %d개, 건물 %d동", len(done_tiles), len(all_buildings))
    logger.info("타일 %d개 수집 시작 bbox=%s", len(tiles), bbox)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    failed = 0
    for i, tile in enumerate(tiles, 1):
        if i in done_tiles:
            continue
        try:
            got = fetch_tile(tile, i)
        except requests.RequestException as exc:
            failed += 1
            logger.warning("타일 %d/%d 최종 실패(건너뜀): %s", i, len(tiles), exc)
            continue
        all_buildings.extend(got)
        done_tiles.add(i)
        out_path.write_text(json.dumps(all_buildings, ensure_ascii=False), encoding="utf-8")
        state_path.write_text(json.dumps(sorted(done_tiles)), encoding="utf-8")
        logger.info("타일 %d/%d — +%d (누계 %d)", i, len(tiles), len(got), len(all_buildings))
        time.sleep(_SLEEP_BETWEEN_TILES_S)

    logger.info(
        "저장 완료: %s (건물 %d동, 최종 실패 타일 %d — 재실행 시 이어받음)",
        out_path,
        len(all_buildings),
        failed,
    )


if __name__ == "__main__":
    main()
