from fastapi import FastAPI
from fastapi.testclient import TestClient

from gildle.adapter.inbound.api import gildle_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(gildle_router)
    return TestClient(app)


def test_app_version_reads_env(monkeypatch):
    monkeypatch.setenv("GILDLE_APP_MIN_VERSION", "1.2.0")
    monkeypatch.setenv("GILDLE_APP_LATEST_VERSION", "1.3.0")
    monkeypatch.delenv("GILDLE_APP_STORE_URL", raising=False)
    data = _client().get("/gildle/app/version?platform=android").json()
    assert data == {
        "platform": "android",
        "min_version": "1.2.0",
        "latest_version": "1.3.0",
        "store_url": None,
    }


def test_app_version_unknown_platform_400():
    assert _client().get("/gildle/app/version?platform=ios").status_code == 400


def test_push_tokens_require_login():
    c = _client()
    assert c.post("/gildle/push-tokens", json={"token": "x"}).status_code == 401
    assert c.request("DELETE", "/gildle/push-tokens", json={"token": "x"}).status_code == 401
