from fastapi import FastAPI
from fastapi.testclient import TestClient

from gildle.adapter.inbound.api import gildle_router


def _client() -> TestClient:
    # 전체 main 앱(DB lifespan/auth) 대신 gildle 라우터만 단독 마운트해 검증한다.
    app = FastAPI()
    app.include_router(gildle_router)
    return TestClient(app)


_START_END = {
    "start_lat": 37.5260,
    "start_lng": 126.9245,
    "end_lat": 37.5270,
    "end_lng": 126.9290,
}


class TestCalculateRouteEndpoint:
    def test_spring_picks_cherry_road_path(self):
        client = _client()
        resp = client.post(
            "/gildle/routes", json={**_START_END, "mode": "spring_autumn"}
        )
        assert resp.status_code == 200
        # 봄/가을: 벚나무 '여의대로' 30% 감면 → 여의대로 경로 선택.
        assert resp.json()["path"] == ["N1", "N2", "N5"]

    def test_winter_avoids_hazard_path(self):
        client = _client()
        resp = client.post(
            "/gildle/routes", json={**_START_END, "mode": "winter_safety"}
        )
        assert resp.status_code == 200
        # 겨울: 여의대로 N1-N2가 결빙구역 근처라 500% 증가 → 샛길로 우회.
        assert resp.json()["path"] == ["N1", "N3", "N5"]

    def test_invalid_mode_returns_400(self):
        client = _client()
        resp = client.post("/gildle/routes", json={**_START_END, "mode": "summer"})
        assert resp.status_code == 400


class TestMapDataEndpoint:
    def test_spring_returns_tree_segments(self):
        client = _client()
        resp = client.get("/gildle/map-data", params={"mode": "spring_autumn"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "spring_autumn"
        assert len(body["tree_segments"]) == 3
        assert body["hazard_zones"] == []

    def test_winter_returns_seoul_hazards_only(self):
        client = _client()
        resp = client.get("/gildle/map-data", params={"mode": "winter_safety"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["tree_segments"] == []
        # 샘플 데이터의 부산 행은 서울 필터로 제외 → 1건.
        assert len(body["hazard_zones"]) == 1

    def test_invalid_mode_returns_400(self):
        client = _client()
        resp = client.get("/gildle/map-data", params={"mode": "summer"})
        assert resp.status_code == 400
