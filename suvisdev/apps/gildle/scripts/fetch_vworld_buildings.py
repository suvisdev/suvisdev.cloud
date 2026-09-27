"""브이월드 도로명주소 건물(LT_C_SPBD) 수집 — 폴리곤 + 지상층수 (2026-09-22).

OSM 대체. `fetch_osm_buildings.py`와 **같은 형식**으로 저장하므로
`compute_shade_scores.py`는 수정 없이 그대로 돌아간다.

왜 바꾸나(2026-09-22 실측):

| 출처 | 높이/층수 보유율 |
|------|------------------|
| OSM `height` 태그 | **10.6%** — 9할이 기본값 6m로 들어가 그늘 계산이 무의미했다 |
| 브이월드 `gro_flo_co` | **83.6%** (표본 5,000동, 서울 5개 지역) |

높이(m)가 아니라 **지상층수**가 오므로 층당 3.0m로 환산한다. 건축HUB
건축물대장도 `heit`(높이)는 공식 예시조차 0이고 `grndFlrCnt`(층수)만 채워져
있어, 층수 기반 환산이 이 도메인의 현실적인 선택이다.

사용법(suvisdev/에서, .env의 VWORLD_API_KEY 사용):
    PYTHONPATH=apps python -m gildle.scripts.fetch_vworld_buildings
    PYTHONPATH=apps python -m gildle.scripts.fetch_vworld_buildings \
        --bbox 37.51 126.90 37.54 126.95        # 부분 테스트

산출물: apps/gildle/data/seoul_buildings_osm.json (gitignore 대상)
        같은 이름을 쓰는 이유는 하위 파이프라인을 건드리지 않기 위해서다.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_OUT = _DATA_DIR / "seoul_buildings_osm.json"
_STATE = _DATA_DIR / "vworld_buildings.state.json"

_SEOUL_BBOX = (37.42, 126.76, 37.70, 127.19)  # south, west, north, east
_TILE_STEP = 0.02
_PAGE_SIZE = 1000  # API 상한(실측: 1001 이상은 오류)
_FLOOR_HEIGHT_M = 3.0  # 층당 높이 — OSM building:levels 환산과 같은 값
_DEFAULT_HEIGHT_M = 6.0  # 층수 결측 시 폴백(OSM 파이프라인과 동일)
_SLEEP_S = 0.2
_MAX_RETRY = 4
_ENDPOINT = "https://api.vworld.kr/req/data"


def _tiles(south: float, west: float, north: float, east: float, step: float):
    out = []
    lat = south
    while lat < north:
        lng = west
        while lng < east:
            out.append((lat, lng, min(lat + step, north), min(lng + step, east)))
            lng += step
        lat += step
    return out


def _request(bbox: tuple[float, float, float, float], page: int, key: str, domain: str) -> dict:
    params = {
        "service": "data",
        "request": "GetFeature",
        "data": "LT_C_SPBD",
        "format": "json",
        "size": _PAGE_SIZE,
        "page": page,
        "crs": "EPSG:4326",
        "geomFilter": f"BOX({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]})",  # minx,miny,maxx,maxy
        "domain": domain,
        "key": key,
    }
    url = f"{_ENDPOINT}?{urllib.parse.urlencode(params)}"
    for attempt in range(_MAX_RETRY):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)["response"]
        except Exception as e:  # noqa: BLE001 — 네트워크 오류는 백오프 후 재시도
            if attempt == _MAX_RETRY - 1:
                raise
            wait = 2**attempt
            logger.warning("요청 실패(%s) — %ds 후 재시도", e, wait)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def _to_building(feature: dict[str, Any]) -> dict[str, Any] | None:
    """API 응답 → 파이프라인 형식(outline/height_m/height_known)."""
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if geom.get("type") == "MultiPolygon":
        rings = coords[0][0] if coords and coords[0] else []
    elif geom.get("type") == "Polygon":
        rings = coords[0] if coords else []
    else:
        return None
    if len(rings) < 3:
        return None

    floors = 0
    try:
        floors = int(feature.get("properties", {}).get("gro_flo_co") or 0)
    except (TypeError, ValueError):
        floors = 0

    return {
        # 응답은 [경도, 위도] 순서다 — 파이프라인은 [위도, 경도]를 쓴다
        "outline": [[float(lat), float(lng)] for lng, lat in rings],
        "height_m": floors * _FLOOR_HEIGHT_M if floors > 0 else _DEFAULT_HEIGHT_M,
        "height_known": floors > 0,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("S", "W", "N", "E"))
    parser.add_argument("--domain", default="suvisdev.cloud")
    parser.add_argument("--reset", action="store_true", help="이어받기 상태를 지우고 처음부터")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    except ImportError:
        pass
    key = os.getenv("VWORLD_API_KEY", "").strip()
    if not key:
        raise SystemExit("VWORLD_API_KEY가 없습니다 (suvisdev/.env)")

    bbox = tuple(args.bbox) if args.bbox else _SEOUL_BBOX
    tiles = _tiles(*bbox, _TILE_STEP)

    done: set[int] = set()
    buildings: list[dict[str, Any]] = []
    if not args.reset and _STATE.exists() and _OUT.exists():
        done = set(json.loads(_STATE.read_text(encoding="utf-8")))
        buildings = json.loads(_OUT.read_text(encoding="utf-8"))
        logger.info("이어받기 — 완료 타일 %d개, 건물 %d동", len(done), len(buildings))

    logger.info("타일 %d개 수집 시작 bbox=%s", len(tiles), bbox)
    for i, tile in enumerate(tiles):
        if i in done:
            continue
        page, got = 1, 0
        while True:
            resp = _request(tile, page, key, args.domain)
            if resp.get("status") != "OK":
                err = (resp.get("error") or {}).get("text", "")
                if "없습니다" in err or resp.get("status") == "NOT_FOUND":
                    break  # 해당 영역에 건물 없음 — 정상
                raise SystemExit(f"API 오류: {err}")
            feats = resp["result"]["featureCollection"]["features"]
            for f in feats:
                b = _to_building(f)
                if b:
                    buildings.append(b)
            got += len(feats)
            if len(feats) < _PAGE_SIZE or page >= int(resp["page"]["total"] or 1):
                break
            page += 1
            time.sleep(_SLEEP_S)

        done.add(i)
        if (i + 1) % 20 == 0 or i == len(tiles) - 1:
            _OUT.write_text(json.dumps(buildings, ensure_ascii=False), encoding="utf-8")
            _STATE.write_text(json.dumps(sorted(done)), encoding="utf-8")
            known = sum(1 for b in buildings if b["height_known"])
            logger.info(
                "타일 %d/%d — 누계 %d동(층수 보유 %d, %.1f%%)",
                i + 1,
                len(tiles),
                len(buildings),
                known,
                known / len(buildings) * 100 if buildings else 0,
            )
        time.sleep(_SLEEP_S)

    _OUT.write_text(json.dumps(buildings, ensure_ascii=False), encoding="utf-8")
    _STATE.write_text(json.dumps(sorted(done)), encoding="utf-8")
    known = sum(1 for b in buildings if b["height_known"])
    logger.info(
        "저장 완료: %s (건물 %d동, 층수 보유 %d동 %.1f%%)",
        _OUT,
        len(buildings),
        known,
        known / len(buildings) * 100 if buildings else 0,
    )


if __name__ == "__main__":
    main()
