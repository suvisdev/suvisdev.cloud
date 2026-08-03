from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from media import router as router_module
from media.dependencies.require_auth import get_current_user
from media.router import media_router
from shared.security.token_verifier import TokenPayload


class _FakeTank:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self._error = error

    def upload_bytes(self, key, data, *, content_type):
        if self._error:
            raise self._error
        self.calls.append({"key": key, "data": data, "content_type": content_type})
        return f"https://fake-bucket.s3.ap-northeast-2.amazonaws.com/{key}"


def _authed_app() -> FastAPI:
    app = FastAPI()
    app.include_router(media_router)
    app.dependency_overrides[get_current_user] = lambda: TokenPayload(
        sub="42", roles=["user"], aud="suvis-susu", exp=9999999999, iat=0, jti="test-jti"
    )
    return app


@pytest.fixture()
def fake_tank():
    return _FakeTank()


@pytest.fixture()
def client(monkeypatch, fake_tank):
    monkeypatch.setattr(router_module, "get_tank", lambda: fake_tank)
    return TestClient(_authed_app())


def test_upload_photo_success(client, fake_tank):
    resp = client.post(
        "/media/photos",
        files={"file": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["size_bytes"] == len(b"fake-image-bytes")
    assert body["content_type"] == "image/jpeg"
    assert body["url"].startswith("https://fake-bucket.s3.")
    assert len(fake_tank.calls) == 1
    assert fake_tank.calls[0]["key"].startswith("media/42/")


def test_upload_photo_rejects_unsupported_content_type(client):
    resp = client.post(
        "/media/photos",
        files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 400


def test_upload_photo_rejects_empty_file(client):
    resp = client.post(
        "/media/photos",
        files={"file": ("photo.jpg", b"", "image/jpeg")},
    )
    assert resp.status_code == 400


def test_upload_photo_maps_s3_failure_to_502(monkeypatch):
    tank = _FakeTank(error=RuntimeError("S3 업로드 실패: boom"))
    monkeypatch.setattr(router_module, "get_tank", lambda: tank)
    client = TestClient(_authed_app())
    resp = client.post(
        "/media/photos",
        files={"file": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert resp.status_code == 502


def test_upload_photo_requires_auth():
    """dependency_override 없이 실제 get_current_user를 태우면 인증 헤더 없을 때 401."""
    app = FastAPI()
    app.include_router(media_router)
    client = TestClient(app)
    resp = client.post(
        "/media/photos",
        files={"file": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert resp.status_code == 401
