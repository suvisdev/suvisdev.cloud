# Gildle 여름 그늘 경로 구현 계획

**Goal:** 출발 시각의 태양 위치와 건물 그림자·가로수를 결합해 그늘 위주로 걷는 경로를 안내하는 `summer_shade` 모드를 gildle에 추가한다(뚜벅 ttubeok.com 방식).

**Architecture:** 배치(노트북)에서 OSM 건물 풋프린트+높이를 수집하고, 대표 한여름 날짜의 시간대별(07~19시, 13슬롯) 태양 위치로 그림자 폴리곤을 캐스팅해 233,964 엣지별 그늘 비율을 사전 계산한다(`shade_scores.json`). 런타임은 요청의 출발 시각을 슬롯에 매핑해 조회만 하고, 햇빛 구간에 강한 페널티(최대 5배)를 주는 다익스트라로 그늘 우선 경로를 만든다. 기존 `SeasonMode`/`RouteWeightCalculator`/`GILDLE_SCORED_EDGES` 패턴을 그대로 따른다.

**Tech Stack:** shapely 2.1.2(이미 설치됨), Overpass API(기존 나무/공원 수집과 동일), 순수 수식 태양 위치(NOAA 근사, 외부 의존 없음), FastAPI, Next.js+react-leaflet.

## Global Constraints

- 사용자 확정: 정밀도 **C(그림자 폴리곤)**, 강제도 **그늘 강력 우선**(경로는 항상 나오고 그늘 비율 표시, 엄격 차단 없음).
- 모드 문자열은 `summer_shade` (기존 `spring_autumn`/`winter_safety`와 나란히).
- 대표 날짜 `2026-08-01`, 슬롯 `07..19` KST 정시 13개. 슬롯 밖(밤)은 그늘 가중 없이 최단 경로 + 응답 `night: true`.
- 페널티 상수 `_SUN_PENALTY_RATE = 4.0` → 완전 햇빛 구간 가중 5배(= base × (1 + 4.0 × (1 - shade))).
- 나무 그늘 결합: `shade = min(1.0, building_frac + 0.6 × tree_score)`.
- 건물 높이 결정: `height` 태그(m) → `building:levels` × 3.0m → 기본 6.0m.
- 신규 대용량 파일은 커밋하지 않는다: `apps/gildle/data/seoul_buildings_osm.json`(수집 원본), `apps/gildle/data/shade_scores.json`(산출) 모두 `.gitignore` 등재. EC2 반영은 scp(호스트 bind mount, 재빌드 불필요).
- 테스트 격리 env var: `GILDLE_SHADE_SCORES`(기존 `GILDLE_SCORED_EDGES` 패턴). 네트워크 필요한 수집 실행은 테스트하지 않고 순수 함수만 테스트.
- 커밋 메시지: Conventional Commits, 한국어, 50자 이내.
- 전 스택 검증: `pytest -m "not gpu and not ollama"` 그린, `pnpm type-check`·`pnpm lint` 그린 유지.

---

## 파일 구조 (전체 조감)

```text
suvisdev/apps/gildle/
├── domain/
│   ├── services/sun_position.py            # 신규 — 순수 태양 위치 수식
│   ├── services/route_weight_calculator.py # 수정 — SUMMER_SHADE 규칙
│   └── value_objects/season_mode.py        # 수정 — SUMMER_SHADE 추가
├── app/
│   ├── ports/input/calculate_route_use_case.py  # 수정 — shade_lookup 파라미터
│   └── use_cases/calculate_route_interactor.py  # 수정 — shade_lookup 전달
├── adapter/inbound/api/
│   ├── schemas/route_schema.py             # 수정 — departure_time
│   └── v1/route_router.py                  # 수정 — shade 로더·응답 확장
├── scripts/
│   ├── fetch_osm_buildings.py              # 신규 — Overpass 건물 수집 배치
│   └── compute_shade_scores.py             # 신규 — 그림자 사전 계산 배치
├── tests/
│   ├── domain/services/test_sun_position.py
│   ├── domain/services/test_route_weight_calculator.py  # 기존에 케이스 추가
│   ├── scripts/test_fetch_osm_buildings.py
│   ├── scripts/test_compute_shade_scores.py
│   └── adapter/test_navigate_shade.py
suvis/app/gildle/map/_components/gildle-map.tsx  # 수정 — 모드·시간·그늘 표시
```

데이터 흐름: `fetch_osm_buildings.py` →(seoul_buildings_osm.json)→ `compute_shade_scores.py` + scored_edges.json →(shade_scores.json)→ 라우터 로더 → weight_fn.

---

### Task 1: 태양 위치 도메인 서비스

**Files:**
- Create: `suvisdev/apps/gildle/domain/services/sun_position.py`
- Test: `suvisdev/apps/gildle/tests/domain/services/test_sun_position.py`

**Interfaces:**
- Produces: `sun_altitude_azimuth(latitude_deg: float, longitude_deg: float, dt_utc: datetime) -> tuple[float, float]` — (고도°, 방위각° 북=0 시계방향). Task 3의 배치가 소비한다.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
"""태양 위치 근사 검증 — 서울 한여름 실측 근사값(±3° 허용)."""

from __future__ import annotations

from datetime import datetime, timezone

from gildle.domain.services.sun_position import sun_altitude_azimuth

_SEOUL_LAT = 37.5665
_SEOUL_LNG = 126.9780


def _kst(hour: int, minute: int = 0) -> datetime:
    # KST = UTC+9. 2026-08-01 기준.
    return datetime(2026, 8, 1, hour - 9, minute, tzinfo=timezone.utc)


def test_noon_high_altitude_south():
    alt, az = sun_altitude_azimuth(_SEOUL_LAT, _SEOUL_LNG, _kst(12, 30))
    assert 66.0 <= alt <= 76.0  # 한여름 남중 고도 근사
    assert 150.0 <= az <= 210.0  # 남쪽


def test_morning_low_altitude_east():
    alt, az = sun_altitude_azimuth(_SEOUL_LAT, _SEOUL_LNG, _kst(8))
    assert 20.0 <= alt <= 40.0
    assert 60.0 <= az <= 110.0  # 동쪽


def test_night_negative_altitude():
    alt, _ = sun_altitude_azimuth(_SEOUL_LAT, _SEOUL_LNG, _kst(23))
    assert alt < 0.0
```

- [ ] **Step 2: 실패 확인**

Run: `cd suvisdev && python -m pytest apps/gildle/tests/domain/services/test_sun_position.py -v`
Expected: FAIL — `ModuleNotFoundError: gildle.domain.services.sun_position`

- [ ] **Step 3: 최소 구현**

```python
"""태양 고도·방위각 근사 계산 — 순수 수식(NOAA 간이 알고리즘).

외부 라이브러리·네트워크 의존 없음. 그늘 배치 계산이 시간 슬롯별 태양
위치를 구할 때 쓴다. 오차 ±1° 수준이면 그림자 길이 용도로 충분하다.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone


def sun_altitude_azimuth(
    latitude_deg: float, longitude_deg: float, dt_utc: datetime
) -> tuple[float, float]:
    """UTC 시각의 태양 (고도°, 방위각° 북=0 시계방향)을 반환한다."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_utc = dt_utc.astimezone(timezone.utc)

    # 율리우스일 기반 경과 세기
    y, m, d = dt_utc.year, dt_utc.month, dt_utc.day
    hours = dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5 + hours / 24
    t = (jd - 2451545.0) / 36525.0

    # 태양 기하 평균 경도·근점이각 → 황경
    l0 = (280.46646 + t * (36000.76983 + 0.0003032 * t)) % 360
    m_anom = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    m_rad = math.radians(m_anom)
    c = (
        (1.914602 - t * (0.004817 + 0.000014 * t)) * math.sin(m_rad)
        + (0.019993 - 0.000101 * t) * math.sin(2 * m_rad)
        + 0.000289 * math.sin(3 * m_rad)
    )
    true_long = l0 + c
    omega = 125.04 - 1934.136 * t
    app_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))

    # 적위
    e0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
    e_corr = e0 + 0.00256 * math.cos(math.radians(omega))
    decl = math.degrees(
        math.asin(math.sin(math.radians(e_corr)) * math.sin(math.radians(app_long)))
    )

    # 균시차(분) → 진태양시 → 시각각
    var_y = math.tan(math.radians(e_corr / 2)) ** 2
    l0_rad = math.radians(l0)
    eot = 4 * math.degrees(
        var_y * math.sin(2 * l0_rad)
        - 2 * 0.016708634 * math.sin(m_rad)
        + 4 * 0.016708634 * var_y * math.sin(m_rad) * math.cos(2 * l0_rad)
        - 0.5 * var_y * var_y * math.sin(4 * l0_rad)
        - 1.25 * 0.016708634**2 * math.sin(2 * m_rad)
    )
    true_solar_min = (hours * 60 + eot + 4 * longitude_deg) % 1440
    hour_angle = true_solar_min / 4 - 180 if true_solar_min / 4 >= 0 else true_solar_min / 4 + 180

    # 고도·방위각
    lat_rad = math.radians(latitude_deg)
    decl_rad = math.radians(decl)
    ha_rad = math.radians(hour_angle)
    zenith = math.acos(
        math.sin(lat_rad) * math.sin(decl_rad)
        + math.cos(lat_rad) * math.cos(decl_rad) * math.cos(ha_rad)
    )
    altitude = 90.0 - math.degrees(zenith)

    az_cos = (math.sin(lat_rad) * math.cos(zenith) - math.sin(decl_rad)) / (
        math.cos(lat_rad) * math.sin(zenith)
    )
    az_cos = max(-1.0, min(1.0, az_cos))
    azimuth = math.degrees(math.acos(az_cos))
    if hour_angle > 0:
        azimuth = (azimuth + 180) % 360
    else:
        azimuth = (540 - azimuth) % 360
    return altitude, azimuth
```

- [ ] **Step 4: 통과 확인**

Run: `cd suvisdev && python -m pytest apps/gildle/tests/domain/services/test_sun_position.py -v`
Expected: PASS 3건. (근사 범위 밖이면 수식 오타 — 허용 범위를 넓히지 말고 구현을 고친다.)

- [ ] **Step 5: 커밋**

```bash
git add suvisdev/apps/gildle/domain/services/sun_position.py suvisdev/apps/gildle/tests/domain/services/test_sun_position.py
git commit -m "feat(gildle): 태양 고도·방위각 순수 계산 서비스"
```

---

### Task 2: OSM 건물 수집 배치 스크립트

**Files:**
- Create: `suvisdev/apps/gildle/scripts/fetch_osm_buildings.py`
- Modify: `.gitignore` (루트) — `suvisdev/apps/gildle/data/seoul_buildings_osm.json`, `suvisdev/apps/gildle/data/shade_scores.json` 두 줄 추가
- Test: `suvisdev/apps/gildle/tests/scripts/test_fetch_osm_buildings.py`

**Interfaces:**
- Produces: `resolve_height_m(tags: dict[str, str]) -> float`, `make_tiles(south: float, west: float, north: float, east: float, step: float) -> list[tuple[float, float, float, float]]`, 실행 산출물 `apps/gildle/data/seoul_buildings_osm.json` = `[{"outline": [[lat, lng], ...], "height_m": float}, ...]`. Task 3이 이 파일 포맷을 소비한다.

- [ ] **Step 1: 실패하는 테스트 작성** (순수 함수만 — 네트워크 호출은 테스트하지 않음)

```python
"""건물 수집 스크립트의 순수 부품 검증(높이 결정·타일 분할)."""

from __future__ import annotations

from gildle.scripts.fetch_osm_buildings import make_tiles, resolve_height_m


def test_height_tag_priority():
    assert resolve_height_m({"height": "25", "building:levels": "3"}) == 25.0


def test_height_tag_with_unit_suffix():
    assert resolve_height_m({"height": "25 m"}) == 25.0


def test_levels_fallback():
    assert resolve_height_m({"building:levels": "5"}) == 15.0  # 5층 × 3.0m


def test_default_height():
    assert resolve_height_m({}) == 6.0


def test_broken_tags_fall_back_to_default():
    assert resolve_height_m({"height": "abc", "building:levels": "?"}) == 6.0


def test_make_tiles_covers_bbox():
    tiles = make_tiles(37.0, 127.0, 37.05, 127.03, step=0.02)
    assert len(tiles) == 3 * 2  # lat 3칸 × lng 2칸(올림)
    assert tiles[0] == (37.0, 127.0, 37.02, 127.02)
    last = tiles[-1]
    assert last[2] >= 37.05 and last[3] >= 127.03
```

- [ ] **Step 2: 실패 확인**

Run: `cd suvisdev && python -m pytest apps/gildle/tests/scripts/test_fetch_osm_buildings.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현**

```python
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
    res = requests.post(_OVERPASS_URL, data={"data": query}, timeout=120)
    res.raise_for_status()
    buildings: list[dict[str, Any]] = []
    for el in res.json().get("elements", []):
        geometry = el.get("geometry") or []
        if len(geometry) < 3:
            continue
        outline = [[p["lat"], p["lon"]] for p in geometry]
        buildings.append(
            {"outline": outline, "height_m": resolve_height_m(el.get("tags", {}))}
        )
    return buildings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--bbox", nargs=4, type=float, default=None,
                        metavar=("SOUTH", "WEST", "NORTH", "EAST"))
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
```

`.gitignore` 추가(기존 gildle data 패턴 근처에):

```text
suvisdev/apps/gildle/data/seoul_buildings_osm.json
suvisdev/apps/gildle/data/shade_scores.json
```

- [ ] **Step 4: 통과 확인**

Run: `cd suvisdev && python -m pytest apps/gildle/tests/scripts/test_fetch_osm_buildings.py -v`
Expected: PASS 6건

- [ ] **Step 5: 소규모 실수집 스모크(네트워크, 커밋 전 1회)**

Run: `cd suvisdev && python apps/gildle/scripts/fetch_osm_buildings.py --bbox 37.52 126.92 37.54 126.94 --out /tmp/claude-1000/-home-a-suvisdev-cloud/09b7bca1-1ae9-4d93-ab0e-a6997d06fefa/scratchpad/buildings_smoke.json`
Expected: exit 0, 로그에 "저장 완료 … 건물 N동"(여의도 일대 수백~수천 동), JSON 파싱 가능

- [ ] **Step 6: 커밋**

```bash
git add suvisdev/apps/gildle/scripts/fetch_osm_buildings.py suvisdev/apps/gildle/tests/scripts/test_fetch_osm_buildings.py .gitignore
git commit -m "feat(gildle): OSM 건물 풋프린트·높이 수집 배치"
```

---

### Task 3: 그림자 사전 계산 배치 스크립트

**Files:**
- Create: `suvisdev/apps/gildle/scripts/compute_shade_scores.py`
- Test: `suvisdev/apps/gildle/tests/scripts/test_compute_shade_scores.py`

**Interfaces:**
- Consumes: Task 1 `sun_altitude_azimuth`, Task 2 산출 포맷(`outline`/`height_m`), 기존 `scored_edges.json`(row에 `from_node/to_node/from_lat/from_lng/to_lat/to_lng/base_distance_m/tree_score`).
- Produces: `shadow_polygons(buildings, sun_alt_deg, sun_az_deg, origin) -> STRtree용 폴리곤 리스트`, `edge_shade_fraction(...)`, 산출물 `apps/gildle/data/shade_scores.json` =
  `{"date": "2026-08-01", "slots": [7, ..., 19], "edges": {"<from_node>-<to_node>": [pct7, ..., pct19]}}` (pct = 0~100 정수). Task 5·6이 이 키 포맷(`from-to`)과 슬롯 순서를 그대로 소비한다.

- [ ] **Step 1: 실패하는 테스트 작성** (합성 건물 1동 + 엣지 2개로 기하 검증)

```python
"""그림자 캐스팅·엣지 교차의 기하 검증 — 합성 데이터."""

from __future__ import annotations

from gildle.scripts.compute_shade_scores import (
    compute_slot_fractions,
    project_to_meters,
)

# 원점(37.53, 126.93) 근처 20m×20m, 높이 30m 건물 하나.
_BUILDING = {
    "outline": [
        [37.5300, 126.9300],
        [37.5300, 126.93023],  # 동쪽으로 약 20m
        [37.53018, 126.93023],  # 북쪽으로 약 20m
        [37.53018, 126.9300],
    ],
    "height_m": 30.0,
}


def _edge(from_lat, from_lng, to_lat, to_lng, key):
    return {
        "from_node": key + "a", "to_node": key + "b",
        "from_lat": from_lat, "from_lng": from_lng,
        "to_lat": to_lat, "to_lng": to_lng,
        "base_distance_m": 30.0, "tree_score": 0.0,
    }


def test_morning_shadow_falls_west():
    # 아침(태양 동쪽) → 그림자는 건물 서쪽. 서쪽 15m 지점의 남북 방향 엣지는
    # 그늘, 동쪽 15m 지점의 엣지는 햇빛이어야 한다.
    west_edge = _edge(37.5300, 126.92983, 37.53018, 126.92983, "w")
    east_edge = _edge(37.5300, 126.93040, 37.53018, 126.93040, "e")
    fr = compute_slot_fractions(
        edges=[west_edge, east_edge], buildings=[_BUILDING],
        sun_alt_deg=30.0, sun_az_deg=90.0,  # 정동, 고도 30°→그림자 길이 52m
    )
    assert fr["wa-wb"] > 60  # 서쪽 엣지: 대부분 그늘
    assert fr["ea-eb"] == 0  # 동쪽 엣지: 햇빛


def test_tree_score_adds_shade():
    sunny = _edge(37.5300, 126.93040, 37.53018, 126.93040, "t")
    sunny["tree_score"] = 0.5
    fr = compute_slot_fractions(
        edges=[sunny], buildings=[], sun_alt_deg=60.0, sun_az_deg=180.0
    )
    assert fr["ta-tb"] == 30  # 0.6 × 0.5 = 0.3 → 30%


def test_project_roundtrip_scale():
    # 위도 1e-4°(≈11.1m)가 미터 좌표에서 10~12m로 투영되는지.
    x0, y0 = project_to_meters(37.5300, 126.9300, 37.53, 126.93)
    x1, y1 = project_to_meters(37.5301, 126.9300, 37.53, 126.93)
    assert abs((y1 - y0) - 11.1) < 1.0 and abs(x1 - x0) < 0.01
```

- [ ] **Step 2: 실패 확인**

Run: `cd suvisdev && python -m pytest apps/gildle/tests/scripts/test_compute_shade_scores.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현**

```python
"""엣지별×시간대별 그늘 비율 사전 계산 배치.

사용법(노트북 — 서울 전역 233k 엣지 × 13슬롯, 수십 분~수 시간):
    python apps/gildle/scripts/compute_shade_scores.py
    python apps/gildle/scripts/compute_shade_scores.py --slots 8 12 16   # 부분 시험

원리: 대표일(2026-08-01) 각 정시 슬롯의 태양 고도·방위각으로 건물마다
그림자 폴리곤(풋프린트 ∪ 그림자 방향 평행이동본 의 convex hull)을 만들고,
STRtree로 엣지 선분과 교차 길이 비율을 구한다. 나무 그늘은
min(1, 건물비율 + 0.6×tree_score)로 결합. 산출은 0~100 정수 퍼센트.
좌표는 등장방형 근사(중심 위도 기준)로 미터 평면에 투영한다.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from datetime import datetime, timezone
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


def _shadow_polygon(outline_m: list[tuple[float, float]], height_m: float,
                    sun_alt_deg: float, sun_az_deg: float) -> Polygon:
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
    result: dict[str, int] = {}

    if sun_alt_deg <= _MIN_SUN_ALT_DEG:
        return {f"{e['from_node']}-{e['to_node']}": 100 for e in edges}

    shadows = [
        _shadow_polygon(
            [project_to_meters(p[0], p[1], lat0, lng0) for p in b["outline"]],
            b["height_m"], sun_alt_deg, sun_az_deg,
        )
        for b in buildings
    ]
    tree = STRtree(shadows) if shadows else None

    for e in edges:
        key = f"{e['from_node']}-{e['to_node']}"
        if "from_lat" not in e or "to_lat" not in e:
            result[key] = 0
            continue
        line = LineString([
            project_to_meters(e["from_lat"], e["from_lng"], lat0, lng0),
            project_to_meters(e["to_lat"], e["to_lng"], lat0, lng0),
        ])
        building_frac = 0.0
        if tree is not None and line.length > 0:
            shaded = 0.0
            for idx in tree.query(line):
                inter = shadows[idx].intersection(line)
                shaded += inter.length
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
        dt_utc = datetime(*_DATE, slot - 9, 0, tzinfo=timezone.utc)  # KST→UTC
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
```

- [ ] **Step 4: 통과 확인**

Run: `cd suvisdev && python -m pytest apps/gildle/tests/scripts/test_compute_shade_scores.py -v`
Expected: PASS 3건

- [ ] **Step 5: 커밋**

```bash
git add suvisdev/apps/gildle/scripts/compute_shade_scores.py suvisdev/apps/gildle/tests/scripts/test_compute_shade_scores.py
git commit -m "feat(gildle): 건물 그림자 기반 그늘 비율 사전 계산 배치"
```

---

### Task 4: 도메인 — SUMMER_SHADE 모드·가중치 규칙

**Files:**
- Modify: `suvisdev/apps/gildle/domain/value_objects/season_mode.py`
- Modify: `suvisdev/apps/gildle/domain/services/route_weight_calculator.py`
- Test: `suvisdev/apps/gildle/tests/domain/services/test_route_weight_calculator.py` (기존 파일에 케이스 추가)

**Interfaces:**
- Produces: `SeasonMode.SUMMER_SHADE`(value `"summer_shade"`), `RouteWeightCalculator.calculate_edge_weight(edge, mode, nearby_segments, nearby_hazards, shade_fraction: float | None = None) -> RouteWeight`. Task 5·6이 이 시그니처를 소비한다.
- shade_fraction: 0.0(전면 햇빛)~1.0(전면 그늘). `None`이면 그늘 데이터 없음 → `edge.tree_score`로 폴백.

- [ ] **Step 1: 실패하는 테스트 추가** (기존 테스트 파일 하단에)

```python
def _summer_edge(tree_score: float = 0.0) -> RouteEdge:
    return RouteEdge(
        from_node="a", to_node="b", base_distance_m=100.0,
        midpoint=Coordinate(latitude=37.53, longitude=126.93),
        road_name=None, tree_score=tree_score,
    )


def test_summer_full_shade_keeps_base_weight():
    calc = RouteWeightCalculator()
    w = calc.calculate_edge_weight(
        _summer_edge(), SeasonMode.SUMMER_SHADE, [], [], shade_fraction=1.0
    )
    assert w.value == 100.0


def test_summer_full_sun_penalized_5x():
    calc = RouteWeightCalculator()
    w = calc.calculate_edge_weight(
        _summer_edge(), SeasonMode.SUMMER_SHADE, [], [], shade_fraction=0.0
    )
    assert w.value == 500.0  # base × (1 + 4.0)


def test_summer_none_falls_back_to_tree_score():
    calc = RouteWeightCalculator()
    w = calc.calculate_edge_weight(
        _summer_edge(tree_score=1.0), SeasonMode.SUMMER_SHADE, [], [], shade_fraction=None
    )
    assert w.value == 100.0  # tree_score 1.0 → 그늘 취급


def test_other_modes_ignore_shade_fraction():
    calc = RouteWeightCalculator()
    w = calc.calculate_edge_weight(
        _summer_edge(), SeasonMode.SPRING_AUTUMN, [], [], shade_fraction=0.0
    )
    assert w.value == 100.0
```

- [ ] **Step 2: 실패 확인**

Run: `cd suvisdev && python -m pytest apps/gildle/tests/domain/services/test_route_weight_calculator.py -v`
Expected: 신규 4건 FAIL(`SUMMER_SHADE` 속성 없음), 기존 케이스는 PASS 유지

- [ ] **Step 3: 구현**

`season_mode.py` — enum 멤버·docstring 한 줄 추가:

```python
    SPRING_AUTUMN = "spring_autumn"
    WINTER_SAFETY = "winter_safety"
    SUMMER_SHADE = "summer_shade"
```

`route_weight_calculator.py` — 상수와 분기 추가:

```python
_SUN_PENALTY_RATE = 4.0  # 완전 햇빛 구간 500% 증가(5배) — 그늘 강력 우선
```

```python
    def calculate_edge_weight(
        self,
        edge: RouteEdge,
        mode: SeasonMode,
        nearby_segments: list[TreeSegment],
        nearby_hazards: list[HazardZone],
        shade_fraction: float | None = None,
    ) -> RouteWeight:
```

기존 두 분기 다음, `return base` 앞에:

```python
        if mode is SeasonMode.SUMMER_SHADE:
            shade = shade_fraction if shade_fraction is not None else edge.tree_score
            shade = max(0.0, min(1.0, shade))
            return base.apply_penalty(_SUN_PENALTY_RATE * (1.0 - shade))
```

(`RouteWeight.apply_penalty(rate)`가 `value × (1 + rate)` 의미인지 기존 구현을 먼저 확인하고, 다르면 그 시맨틱에 맞춘다 — WINTER 5.0이 "500% 증가(6배)" 주석이므로 `1 + rate` 곱으로 예상. 만약 6배라면 테스트 기대값 500.0을 `base×(1+4.0)` 시맨틱에 맞게 유지하기 위해 페널티 인자를 그대로 쓰면 된다.)

- [ ] **Step 4: 통과 확인**

Run: `cd suvisdev && python -m pytest apps/gildle/tests/domain -v`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add suvisdev/apps/gildle/domain/value_objects/season_mode.py suvisdev/apps/gildle/domain/services/route_weight_calculator.py suvisdev/apps/gildle/tests/domain/services/test_route_weight_calculator.py
git commit -m "feat(gildle): SUMMER_SHADE 모드 그늘 가중치 규칙"
```

---

### Task 5: 인터랙터 — shade_lookup 전달

**Files:**
- Modify: `suvisdev/apps/gildle/app/ports/input/calculate_route_use_case.py`
- Modify: `suvisdev/apps/gildle/app/use_cases/calculate_route_interactor.py`
- Test: `suvisdev/apps/gildle/tests/app/use_cases/test_calculate_route_interactor.py` (기존 파일에 케이스 추가 — 없으면 기존 인터랙터 테스트 위치를 `grep -r CalculateDogFriendlyRouteInteractor apps/gildle/tests`로 찾아 그 파일에 추가)

**Interfaces:**
- Consumes: Task 4 `calculate_edge_weight(..., shade_fraction=...)`.
- Produces: `execute(edges, start, end, mode, shade_lookup: Mapping[tuple[str, str], float] | None = None) -> list[str]`. 키는 `(from_node, to_node)` 정방향만 — 없으면 역방향 `(to, from)`도 조회. Task 6이 이 시그니처를 소비한다.

- [ ] **Step 1: 실패하는 테스트 추가**

```python
def test_summer_shade_prefers_shaded_detour():
    """직선(햇빛)보다 우회(그늘)를 고르는지 — 페널티 5배 > 우회 거리 2배."""
    edges = [
        _edge("s", "e", 100.0),          # 직행 100m, 그늘 0%
        _edge("s", "m", 100.0),          # 우회 100m+100m, 그늘 100%
        _edge("m", "e", 100.0),
    ]
    shade = {("s", "e"): 0.0, ("s", "m"): 1.0, ("m", "e"): 1.0}
    interactor = _make_interactor()  # 기존 테스트 파일의 fake 구성 헬퍼 재사용
    path = interactor.execute(edges, "s", "e", SeasonMode.SUMMER_SHADE, shade_lookup=shade)
    assert path == ["s", "m", "e"]


def test_summer_shade_without_lookup_still_routes():
    edges = [_edge("s", "e", 100.0)]
    interactor = _make_interactor()
    path = interactor.execute(edges, "s", "e", SeasonMode.SUMMER_SHADE)
    assert path == ["s", "e"]
```

(`_edge`/`_make_interactor`는 그 파일의 기존 헬퍼를 그대로 쓴다. 없으면 Task 4의 `_summer_edge` 스타일로 최소 작성 — RouteGraphPort는 기존 fake/실어댑터 조립 방식을 파일 상단에서 확인해 따른다.)

- [ ] **Step 2: 실패 확인**

Run: `cd suvisdev && python -m pytest apps/gildle/tests -k interactor -v`
Expected: 신규 FAIL(`execute()`가 shade_lookup 인자를 받지 않음)

- [ ] **Step 3: 구현**

`calculate_route_use_case.py`(입력 포트 ABC) — 시그니처에 동일 파라미터 추가:

```python
from collections.abc import Mapping

    @abstractmethod
    def execute(
        self,
        edges: list[RouteEdge],
        start: str,
        end: str,
        mode: SeasonMode,
        shade_lookup: Mapping[tuple[str, str], float] | None = None,
    ) -> list[str]: ...
```

`calculate_route_interactor.py`:

```python
    def execute(
        self,
        edges: list[RouteEdge],
        start: str,
        end: str,
        mode: SeasonMode,
        shade_lookup: Mapping[tuple[str, str], float] | None = None,
    ) -> list[str]:
        segments = self._tree_repository.find_all()
        hazards = self._hazard_repository.find_all()

        def weight_fn(edge: RouteEdge) -> float:
            shade = None
            if shade_lookup is not None:
                shade = shade_lookup.get((edge.from_node, edge.to_node))
                if shade is None:
                    shade = shade_lookup.get((edge.to_node, edge.from_node))
            return self._weight_calculator.calculate_edge_weight(
                edge, mode, segments, hazards, shade_fraction=shade
            ).value

        graph = self._route_graph.build_graph(edges)
        return self._route_graph.find_shortest_path(graph, start, end, weight_fn)
```

- [ ] **Step 4: 통과 확인**

Run: `cd suvisdev && python -m pytest apps/gildle/tests -v 2>&1 | tail -3`
Expected: gildle 전체 PASS(기존 호출부는 기본값 None으로 하위호환)

- [ ] **Step 5: 커밋**

```bash
git add suvisdev/apps/gildle/app/ports/input/calculate_route_use_case.py suvisdev/apps/gildle/app/use_cases/calculate_route_interactor.py suvisdev/apps/gildle/tests
git commit -m "feat(gildle): 경로 계산에 그늘 lookup 전달"
```

---

### Task 6: 라우터 — shade 로더·departure_time·응답 확장

**Files:**
- Modify: `suvisdev/apps/gildle/adapter/inbound/api/schemas/route_schema.py`
- Modify: `suvisdev/apps/gildle/adapter/inbound/api/v1/route_router.py`
- Test: `suvisdev/apps/gildle/tests/adapter/test_navigate_shade.py` (신규)

**Interfaces:**
- Consumes: Task 3 산출 포맷(`slots`/`edges`의 `"from-to": [pct...]`), Task 5 `execute(..., shade_lookup=...)`.
- Produces: `NavigateRequestSchema.departure_time: str | None`("HH:MM"), navigate 응답에 `shade_ratio: float | None`(0~1, 경로 길이가중 평균)·`edge_shades: list[float] | None`(path 간선 순, 0~1)·`night: bool`. env var `GILDLE_SHADE_SCORES`. Task 7 프론트가 이 응답 필드를 소비한다.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
"""navigate summer_shade — 그늘 lookup 로딩·슬롯 매핑·응답 필드."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

# 기존 gildle 라우터 테스트의 앱 조립 방식을 따른다:
# grep -rn "TestClient" apps/gildle/tests 로 기존 패턴 확인 후 동일하게 작성.
from main import app  # 기존 gildle 테스트가 main.app을 쓰면 그대로, 아니면 라우터 단독 조립


def _write_fixtures(tmp_path, monkeypatch):
    edges = [
        {"from_node": "s", "to_node": "e", "base_distance_m": 100.0,
         "midpoint_lat": 37.53, "midpoint_lng": 126.93,
         "from_lat": 37.53, "from_lng": 126.93, "to_lat": 37.531, "to_lng": 126.93,
         "tree_score": 0.0, "hazard_score": 0.0, "dog_friendly_score": 0.0},
        {"from_node": "s", "to_node": "m", "base_distance_m": 100.0,
         "midpoint_lat": 37.53, "midpoint_lng": 126.931,
         "from_lat": 37.53, "from_lng": 126.93, "to_lat": 37.53, "to_lng": 126.932,
         "tree_score": 0.0, "hazard_score": 0.0, "dog_friendly_score": 0.0},
        {"from_node": "m", "to_node": "e", "base_distance_m": 100.0,
         "midpoint_lat": 37.5305, "midpoint_lng": 126.931,
         "from_lat": 37.53, "from_lng": 126.932, "to_lat": 37.531, "to_lng": 126.93,
         "tree_score": 0.0, "hazard_score": 0.0, "dog_friendly_score": 0.0},
    ]
    shade = {"date": "2026-08-01", "slots": [7, 8],
             "edges": {"s-e": [0, 0], "s-m": [100, 100], "m-e": [100, 100]}}
    edges_path = tmp_path / "edges.json"
    shade_path = tmp_path / "shade.json"
    edges_path.write_text(json.dumps(edges), encoding="utf-8")
    shade_path.write_text(json.dumps(shade), encoding="utf-8")
    monkeypatch.setenv("GILDLE_SCORED_EDGES", str(edges_path))
    monkeypatch.setenv("GILDLE_SHADE_SCORES", str(shade_path))


def test_summer_shade_takes_detour_and_reports_ratio(tmp_path, monkeypatch):
    _write_fixtures(tmp_path, monkeypatch)
    client = TestClient(app)
    res = client.post("/api/gildle/navigate", json={
        "start_node": "s", "end_node": "e",
        "mode": "summer_shade", "departure_time": "08:00",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["path"] == ["s", "m", "e"]
    assert data["night"] is False
    assert data["shade_ratio"] == 1.0
    assert data["edge_shades"] == [1.0, 1.0]


def test_night_departure_skips_shade(tmp_path, monkeypatch):
    _write_fixtures(tmp_path, monkeypatch)
    client = TestClient(app)
    res = client.post("/api/gildle/navigate", json={
        "start_node": "s", "end_node": "e",
        "mode": "summer_shade", "departure_time": "23:00",
    })
    data = res.json()
    assert data["path"] == ["s", "e"]  # 밤 — 최단 직행
    assert data["night"] is True
    assert data["shade_ratio"] is None


def test_other_modes_response_unchanged_shape(tmp_path, monkeypatch):
    _write_fixtures(tmp_path, monkeypatch)
    client = TestClient(app)
    res = client.post("/api/gildle/navigate", json={
        "start_node": "s", "end_node": "e", "mode": "spring_autumn",
    })
    data = res.json()
    assert data["path"] == ["s", "e"]
    assert data["shade_ratio"] is None and data["night"] is False
```

주의: 기존 라우터 모듈 전역 캐시(`_route_edges_cache`)가 테스트 간 오염되므로, 테스트마다 `route_router._route_edges_cache = None`·`_shade_cache = None`을 리셋하는 autouse fixture를 파일에 포함한다(8/26 core/lol 서킷 리셋과 같은 패턴):

```python
import pytest
from gildle.adapter.inbound.api.v1 import route_router as rr


@pytest.fixture(autouse=True)
def _reset_router_caches():
    rr._route_edges_cache = None
    rr._scored_edges_cache = None
    rr._shade_cache = None
    yield
```

- [ ] **Step 2: 실패 확인**

Run: `cd suvisdev && python -m pytest apps/gildle/tests/adapter/test_navigate_shade.py -v`
Expected: FAIL(`departure_time` 미지원 / `_shade_cache` 없음)

- [ ] **Step 3: 구현**

`route_schema.py` — `NavigateRequestSchema`에 필드 추가:

```python
    departure_time: str | None = Field(
        None, description='출발 시각 "HH:MM"(KST). summer_shade에서만 사용, 미지정 시 현재 시각.'
    )
```

`route_router.py` — 로더·슬롯 매핑·navigate 확장:

```python
_shade_cache: dict[str, Any] | None = None
_shade_mtime: float = 0.0


def _load_shade_scores() -> dict[str, Any] | None:
    """shade_scores.json 로더 — scored_edges와 동일한 mtime 캐시 패턴."""
    global _shade_cache, _shade_mtime  # noqa: PLW0603
    path = Path(os.getenv("GILDLE_SHADE_SCORES", str(_DATA_DIR / "shade_scores.json")))
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    if _shade_cache is not None and mtime == _shade_mtime:
        return _shade_cache
    _shade_cache = json.loads(path.read_text(encoding="utf-8"))
    _shade_mtime = mtime
    return _shade_cache


def _resolve_slot(departure_time: str | None, slots: list[int]) -> int | None:
    """"HH:MM"을 가장 가까운 슬롯 시(hour)로 매핑. 슬롯 범위 밖(밤)이면 None."""
    from datetime import datetime, timedelta, timezone

    if departure_time:
        try:
            hour = int(departure_time.split(":")[0])
            minute = int(departure_time.split(":")[1])
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail='departure_time은 "HH:MM" 형식')
    else:
        now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
        hour, minute = now_kst.hour, now_kst.minute
    slot = hour + (1 if minute >= 30 else 0)
    if slot not in slots:
        return None
    return slot


def _build_shade_lookup(slot: int) -> dict[tuple[str, str], float] | None:
    data = _load_shade_scores()
    if data is None:
        return None
    idx = data["slots"].index(slot)
    lookup: dict[tuple[str, str], float] = {}
    for key, pcts in data["edges"].items():
        from_node, _, to_node = key.partition("-")
        lookup[(from_node, to_node)] = pcts[idx] / 100.0
    return lookup
```

`navigate()` 본문 수정 — season 파싱 뒤:

```python
    shade_lookup: dict[tuple[str, str], float] | None = None
    night = False
    if season is SeasonMode.SUMMER_SHADE:
        shade_data = _load_shade_scores()
        slots = shade_data["slots"] if shade_data else list(range(7, 20))
        slot = _resolve_slot(request.departure_time, slots)
        if slot is None:
            night = True
        elif shade_data is not None:
            shade_lookup = _build_shade_lookup(slot)

    path = use_case.execute(edges, request.start_node, request.end_node, season,
                            shade_lookup=shade_lookup)
```

응답 조립 — coordinates 계산 다음, 경로 간선의 그늘·길이가중 평균:

```python
    edge_shades: list[float] | None = None
    shade_ratio: float | None = None
    if season is SeasonMode.SUMMER_SHADE and shade_lookup is not None and len(path) >= 2:
        edge_shades = []
        total_len = 0.0
        shaded_len = 0.0
        for i in range(len(path) - 1):
            edge = edge_lookup.get((path[i], path[i + 1]))
            shade = 0.0
            if edge is not None:
                shade = shade_lookup.get((edge.from_node, edge.to_node), 0.0)
                total_len += edge.base_distance_m
                shaded_len += edge.base_distance_m * shade
            edge_shades.append(round(shade, 2))
        shade_ratio = round(shaded_len / total_len, 2) if total_len > 0 else None

    return {
        "path": path,
        "coordinates": coordinates,
        "shade_ratio": shade_ratio,
        "edge_shades": edge_shades,
        "night": night,
    }
```

- [ ] **Step 4: 통과 확인**

Run: `cd suvisdev && python -m pytest apps/gildle/tests -v 2>&1 | tail -3` 후 전체 `python -m pytest -m "not gpu and not ollama" -q 2>&1 | tail -2`
Expected: gildle 전체 PASS + 전체 스위트 그린

- [ ] **Step 5: 커밋**

```bash
git add suvisdev/apps/gildle/adapter/inbound/api/schemas/route_schema.py suvisdev/apps/gildle/adapter/inbound/api/v1/route_router.py suvisdev/apps/gildle/tests/adapter/test_navigate_shade.py
git commit -m "feat(gildle): navigate 그늘 슬롯 조회·응답 확장"
```

---

### Task 7: 프론트 — 여름 그늘 모드 UI

**Files:**
- Modify: `suvis/app/gildle/map/_components/gildle-map.tsx`

**Interfaces:**
- Consumes: Task 6 응답 `shade_ratio`/`edge_shades`/`night`, 요청 `departure_time`.

- [ ] **Step 1: 모드·상태 추가**

`SeasonMode` 타입(파일 내 정의 확인 후)에 `"summer_shade"` 추가, 모드 선택 UI 객체(81행 근처 `spring_autumn: { label: ... }`)에 추가:

```ts
  summer_shade: { label: "여름 (그늘 우선)" },
```

시간 상태(기본 현재 시각 "HH:MM"):

```ts
  const [departureTime, setDepartureTime] = useState<string>(() => {
    const now = new Date()
    return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`
  })
  const [routeShade, setRouteShade] = useState<{ ratio: number | null; night: boolean } | null>(null)
```

- [ ] **Step 2: navigate 호출 확장** (385행 fetch)

```ts
      body: JSON.stringify({
        start_node: startPoint.nodeId,
        end_node: endPoint.nodeId,
        mode: season,
        ...(season === "summer_shade" ? { departure_time: departureTime } : {}),
      }),
```

응답 타입에 `shade_ratio: number | null; edge_shades: number[] | null; night: boolean` 추가, 성공 시:

```ts
        setRouteShade(season === "summer_shade" ? { ratio: data.shade_ratio, night: data.night } : null)
```

`useEffect` deps에 `departureTime` 추가(summer_shade일 때 시간 변경이 재탐색 트리거).

- [ ] **Step 3: 구간 색상** — `RouteSegment`에 `shade: number | null` 추가하고 segments 조립 시 `data.edge_shades?.[edgeIdx] ?? null` 저장. Polyline 색: summer_shade 모드에서 `shade >= 0.6`이면 기존 경로색(그늘), 아니면 주황(`#f59e0b`, 햇빛 구간). 다른 모드는 기존 색 유지.

- [ ] **Step 4: UI** — 모드 셀렉터 옆에 summer_shade일 때만 `<input type="time" value={departureTime} onChange={...}>` 노출. 경로 상세 카드(694행 근처)에:

```tsx
  {routeShade && !routeShade.night && routeShade.ratio !== null && (
    <p>🌳 그늘 비율: {Math.round(routeShade.ratio * 100)}%</p>
  )}
  {routeShade?.night && <p>🌙 밤 시간대 — 최단 경로로 안내합니다</p>}
```

(정확한 마크업·클래스는 주변 기존 카드 스타일을 그대로 따른다 — gildle 전용 CSS 토큰 규칙.)

- [ ] **Step 5: 검증**

Run: `cd suvis && pnpm type-check && pnpm lint`
Expected: 0 errors (기존 경고 1건만)

- [ ] **Step 6: 커밋**

```bash
git add suvis/app/gildle/map/_components/gildle-map.tsx
git commit -m "feat(gildle): 여름 그늘 모드 UI·시간 선택·그늘 표시"
```

---

### Task 8: 실데이터 배치 실행 + 로컬 E2E + 배포

**Files:** 코드 변경 없음(데이터 산출·검증·배포만)

- [ ] **Step 1: 서울 전역 건물 수집** (노트북, 네트워크 — 20~40분)

Run: `cd suvisdev && python apps/gildle/scripts/fetch_osm_buildings.py 2>&1 | tail -5`
Expected: "저장 완료 … 건물 N동"(수십만 동), 실패 타일은 경고 후 건너뜀

- [ ] **Step 2: 전 슬롯 그늘 계산** (수십 분~수 시간 — 우선 `--slots 8 13 17`로 시험 후 전체)

Run: `cd suvisdev && python apps/gildle/scripts/compute_shade_scores.py 2>&1 | tail -5`
Expected: "저장 완료 … 엣지 233964", 슬롯별 태양 고도 로그가 아침 낮음→정오 최고→저녁 낮음 곡선

- [ ] **Step 3: 로컬 E2E** — 백엔드 `python main.py` + 프론트 `pnpm dev`로 `/gildle/map`에서 여름 그늘 모드 선택, 08:00와 17:00로 같은 출발/도착을 비교 — 경로·그늘 비율이 달라지는지(아침엔 건물 동측 도로가 햇빛, 저녁엔 서측이 햇빛) 눈으로 확인. 스크린샷 확보.

- [ ] **Step 4: EC2 반영** — 코드는 push 후 `~/auto-deploy.sh backend`, 데이터는 scp:

```bash
scp suvisdev/apps/gildle/data/shade_scores.json aws:~/suvisdev.cloud/suvisdev/apps/gildle/data/
```

(bind mount라 재빌드 불필요 — 8/25 gildle data 마운트 확인됨. `seoul_buildings_osm.json` 원본은 EC2에 안 올린다.)

- [ ] **Step 5: 프로덕션 확인** — 실제 지도에서 여름 그늘 경로 1회 왕복 확인, WORK_LOG_GILDLE에 당일 기록, PROGRESS 완료 등재 후 문서 커밋.

---

## Self-Review 체크 결과

- **스펙 커버리지**: 시간대별 태양(T1·T6 슬롯), 건물 그림자(T2·T3), 나무 결합(T3), 그늘 강력 우선(T4), 시간 선택 UI·그늘 비율 표시(T7), 밤 처리(T6·T7) — 커버됨. 뚜벅의 "구간별 통과 예정 시각" 세분화는 의도적 미포함(출발 시각 단일 슬롯 — 도보 1시간 내 태양 이동 ~15°로 오차 허용, 한계로 문서화).
- **플레이스홀더 스캔**: 기존 파일의 헬퍼 재사용 지점 2곳(T5 `_make_interactor`, T6 앱 조립)은 "기존 패턴을 grep으로 확인 후 따른다"로 명시 — 실행 시점에 실물 확인 필요, TBD 아님.
- **타입 일관성**: `shade_fraction: float | None`(T4) ↔ `shade_lookup: Mapping[tuple[str, str], float] | None`(T5) ↔ pct int→/100 변환(T6) ↔ 프론트 `edge_shades: number[]`(T6→T7) 일치 확인.
