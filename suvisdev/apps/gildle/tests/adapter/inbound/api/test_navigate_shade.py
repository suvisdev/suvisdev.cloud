"""navigate summer_shade — 그늘 lookup 로딩·슬롯 매핑·응답 필드."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gildle.adapter.inbound.api import gildle_router
from gildle.adapter.inbound.api.v1 import route_router as rr


@pytest.fixture(autouse=True)
def _reset_router_caches():
    # 모듈 전역 mtime 캐시가 테스트 간 오염되지 않게 리셋(8/26 서킷 리셋과 동일 패턴).
    rr._route_edges_cache = None
    rr._scored_edges_cache = None
    rr._shade_cache = None
    yield


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(gildle_router)
    return TestClient(app)


def _write_fixtures(tmp_path: Path, monkeypatch) -> None:
    # 직행 s-e(그늘 0%) vs 우회 s-m-e(그늘 100%). 페널티 5배 > 우회 2배 거리.
    edges = [
        {
            "from_node": "s",
            "to_node": "e",
            "base_distance_m": 100.0,
            "midpoint_lat": 37.53,
            "midpoint_lng": 126.93,
            "from_lat": 37.530,
            "from_lng": 126.930,
            "to_lat": 37.531,
            "to_lng": 126.930,
            "tree_score": 0.0,
            "hazard_score": 0.0,
            "dog_friendly_score": 0.0,
        },
        {
            "from_node": "s",
            "to_node": "m",
            "base_distance_m": 100.0,
            "midpoint_lat": 37.530,
            "midpoint_lng": 126.931,
            "from_lat": 37.530,
            "from_lng": 126.930,
            "to_lat": 37.530,
            "to_lng": 126.932,
            "tree_score": 0.0,
            "hazard_score": 0.0,
            "dog_friendly_score": 0.0,
        },
        {
            "from_node": "m",
            "to_node": "e",
            "base_distance_m": 100.0,
            "midpoint_lat": 37.5305,
            "midpoint_lng": 126.931,
            "from_lat": 37.530,
            "from_lng": 126.932,
            "to_lat": 37.531,
            "to_lng": 126.930,
            "tree_score": 0.0,
            "hazard_score": 0.0,
            "dog_friendly_score": 0.0,
        },
    ]
    shade = {
        "date": "2026-08-01",
        "slots": [7, 8],
        "edges": {"s-e": [0, 0], "s-m": [100, 100], "m-e": [100, 100]},
    }
    edges_path = tmp_path / "edges.json"
    shade_path = tmp_path / "shade.json"
    edges_path.write_text(json.dumps(edges), encoding="utf-8")
    shade_path.write_text(json.dumps(shade), encoding="utf-8")
    monkeypatch.setenv("GILDLE_SCORED_EDGES", str(edges_path))
    monkeypatch.setenv("GILDLE_SHADE_SCORES", str(shade_path))


def test_summer_shade_takes_detour_and_reports_ratio(tmp_path, monkeypatch):
    _write_fixtures(tmp_path, monkeypatch)
    resp = _client().post(
        "/gildle/navigate",
        json={
            "start_node": "s",
            "end_node": "e",
            "mode": "summer_shade",
            "departure_time": "08:00",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["path"] == ["s", "m", "e"]
    assert data["night"] is False
    assert data["shade_ratio"] == 1.0
    assert data["edge_shades"] == [1.0, 1.0]


def test_night_departure_skips_shade(tmp_path, monkeypatch):
    # 밤 판정은 실제 태양 고도 기반(일출·일몰 자동 연동) — 23시는 계절 무관 밤.
    _write_fixtures(tmp_path, monkeypatch)
    resp = _client().post(
        "/gildle/navigate",
        json={
            "start_node": "s",
            "end_node": "e",
            "mode": "summer_shade",
            "departure_time": "23:00",
        },
    )
    data = resp.json()
    assert data["path"] == ["s", "e"]  # 밤 — 그늘 계산 제외, 최단 직행
    assert data["night"] is True
    assert data["shade_ratio"] is None


def test_midday_out_of_slot_clamps_not_night(tmp_path, monkeypatch):
    # 정오는 계절 무관 낮. 픽스처 슬롯이 [7, 8]뿐이어도 밤 처리하지 않고
    # 가장 가까운 슬롯(8시)으로 클램프해 그늘 가중을 적용해야 한다.
    _write_fixtures(tmp_path, monkeypatch)
    resp = _client().post(
        "/gildle/navigate",
        json={
            "start_node": "s",
            "end_node": "e",
            "mode": "summer_shade",
            "departure_time": "12:00",
        },
    )
    data = resp.json()
    assert data["night"] is False
    assert data["path"] == ["s", "m", "e"]  # 8시 슬롯 그늘로 우회 선택


def test_bad_departure_time_returns_400(tmp_path, monkeypatch):
    _write_fixtures(tmp_path, monkeypatch)
    resp = _client().post(
        "/gildle/navigate",
        json={
            "start_node": "s",
            "end_node": "e",
            "mode": "summer_shade",
            "departure_time": "여덟시",
        },
    )
    assert resp.status_code == 400


def test_other_modes_response_unchanged_shape(tmp_path, monkeypatch):
    _write_fixtures(tmp_path, monkeypatch)
    resp = _client().post(
        "/gildle/navigate",
        json={"start_node": "s", "end_node": "e", "mode": "spring_autumn"},
    )
    data = resp.json()
    assert data["path"] == ["s", "e"]
    assert data["shade_ratio"] is None and data["night"] is False


def test_routes_endpoint_applies_summer_shade_like_navigate(tmp_path, monkeypatch):
    # 앱은 좌표만 알기 때문에 /routes도 /navigate와 같은 그늘 탐색·응답 필드를 가져야 한다
    # (2026-09-27 이전엔 /routes가 여름 모드를 나무 점수 폴백으로만 돌렸다).
    _write_fixtures(tmp_path, monkeypatch)
    resp = _client().post(
        "/gildle/routes",
        json={
            "start_lat": 37.530,
            "start_lng": 126.930,
            "end_lat": 37.531,
            "end_lng": 126.930,
            "mode": "summer_shade",
            "departure_time": "08:00",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["path"] == ["s", "m", "e"]
    assert data["shade_ratio"] == 1.0
    assert data["edge_shades"] == [1.0, 1.0]
    assert data["night"] is False
    assert data["length_m"] == 200.0


def test_coordinates_follow_path_direction_on_reversed_edges(tmp_path, monkeypatch):
    # 간선이 (a,b)·(c,b)로 저장돼 있어도 경로 a→b→c의 좌표는 a,b,c 순이어야 한다.
    # 예전 코드는 항상 from_coord를 써서 a,c,b(지그재그)가 나왔다.
    def edge(u, v, ulat, ulng, vlat, vlng):
        return {
            "from_node": u,
            "to_node": v,
            "base_distance_m": 100.0,
            "midpoint_lat": (ulat + vlat) / 2,
            "midpoint_lng": (ulng + vlng) / 2,
            "from_lat": ulat,
            "from_lng": ulng,
            "to_lat": vlat,
            "to_lng": vlng,
            "tree_score": 0.0,
            "hazard_score": 0.0,
            "dog_friendly_score": 0.0,
        }

    edges = [
        edge("a", "b", 37.500, 127.000, 37.501, 127.000),
        edge("c", "b", 37.502, 127.000, 37.501, 127.000),
    ]
    edges_path = tmp_path / "edges.json"
    edges_path.write_text(json.dumps(edges), encoding="utf-8")
    monkeypatch.setenv("GILDLE_SCORED_EDGES", str(edges_path))

    resp = _client().post(
        "/gildle/navigate", json={"start_node": "a", "end_node": "c", "mode": "spring_autumn"}
    )
    data = resp.json()
    assert data["path"] == ["a", "b", "c"]
    assert data["coordinates"] == [[37.500, 127.0], [37.501, 127.0], [37.502, 127.0]]
    assert data["length_m"] == 200.0
