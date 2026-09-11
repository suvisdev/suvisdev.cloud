from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from shared.security.require_admin import AdminPrincipal, require_admin
from shared.security.token_verifier import TokenPayload

from media import router as router_module
from media.dependencies.require_auth import get_current_user
from media.router import media_router


class _FakeTank:
    def __init__(
        self,
        *,
        error: Exception | None = None,
        objects: dict[str, bytes] | None = None,
        list_error: Exception | None = None,
    ) -> None:
        self.calls: list[dict] = []
        self._error = error
        self._objects = objects or {}
        self._list_error = list_error

    def upload_bytes(self, key, data, *, content_type):
        if self._error:
            raise self._error
        self.calls.append({"key": key, "data": data, "content_type": content_type})
        return f"https://fake-bucket.s3.ap-northeast-2.amazonaws.com/{key}"

    def list_objects(self, prefix, *, bucket=None):
        if self._list_error:
            raise self._list_error
        return [key for key in self._objects if key.startswith(prefix)]

    def download_bytes(self, key, *, bucket=None):
        return self._objects[key]

    def generate_presigned_url(self, key, *, expires_in=3600, bucket=None):
        return f"https://fake-bucket.s3.ap-northeast-2.amazonaws.com/{key}?presigned=1"


def _authed_app() -> FastAPI:
    app = FastAPI()
    app.include_router(media_router)
    app.dependency_overrides[get_current_user] = lambda: TokenPayload(
        sub="42", roles=["user"], aud="suvis-susu", exp=9999999999, iat=0, jti="test-jti"
    )
    app.dependency_overrides[require_admin] = lambda: AdminPrincipal(
        user_id=42, username="admin-42"
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


def test_upload_photo_rejects_oversize_without_full_read(monkeypatch, client, fake_tank):
    """상한 초과 파일은 400 — 상한+1바이트까지만 읽고 거부한다."""
    monkeypatch.setattr(router_module, "_MAX_BYTES", 8)
    resp = client.post(
        "/media/photos",
        files={"file": ("photo.jpg", b"123456789", "image/jpeg")},
    )
    assert resp.status_code == 400
    assert fake_tank.calls == []


def test_upload_photo_maps_s3_failure_to_502(monkeypatch):
    tank = _FakeTank(error=RuntimeError("S3 업로드 실패: boom"))
    monkeypatch.setattr(router_module, "get_tank", lambda: tank)
    client = TestClient(_authed_app())
    resp = client.post(
        "/media/photos",
        files={"file": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert resp.status_code == 502
    # 원시 예외 문자열(버킷명·자격증명 힌트 등)을 응답에 흘리지 않는다
    assert "boom" not in resp.json()["detail"]


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


def test_list_photos_with_ocr_shows_all_users_sorted_newest_first(monkeypatch):
    tank = _FakeTank(
        objects={
            "media/42/20260101_000000_a.jpg": b"img-a",
            "media/42/20260201_000000_b.jpg": b"img-b",
            "media/7/20260301_000000_other-user.jpg": b"img-other",
        }
    )
    monkeypatch.setattr(router_module, "get_tank", lambda: tank)
    monkeypatch.setattr(router_module, "extract_text", lambda content, content_type: "hello")
    client = TestClient(_authed_app())

    resp = client.get("/media/photos/ocr")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3  # admin은 다른 사용자 사진도 전부 봄
    assert body[0]["image_url"].endswith("20260301_000000_other-user.jpg?presigned=1")
    assert body[0]["user_id"] == "7"
    assert body[0]["extracted_text"] == "hello"
    assert body[1]["user_id"] == "42"


def test_list_photos_with_ocr_falls_back_on_per_item_ocr_failure(monkeypatch):
    tank = _FakeTank(objects={"media/42/20260101_000000_a.jpg": b"img-a"})

    def _boom(content, content_type):
        raise RuntimeError("Gemini OCR 호출 실패: boom")

    monkeypatch.setattr(router_module, "get_tank", lambda: tank)
    monkeypatch.setattr(router_module, "extract_text", _boom)
    client = TestClient(_authed_app())

    resp = client.get("/media/photos/ocr")

    assert resp.status_code == 200
    assert resp.json()[0]["extracted_text"] == "(텍스트 추출 실패)"


def test_list_photos_with_ocr_maps_list_failure_to_502(monkeypatch):
    tank = _FakeTank(list_error=RuntimeError("S3 목록 조회 실패: boom"))
    monkeypatch.setattr(router_module, "get_tank", lambda: tank)
    client = TestClient(_authed_app())

    resp = client.get("/media/photos/ocr")

    assert resp.status_code == 502
    assert "boom" not in resp.json()["detail"]


def test_list_photos_with_ocr_requires_admin():
    """dependency_override 없이 실제 require_admin을 태우면 인증 헤더 없을 때 401."""
    app = FastAPI()
    app.include_router(media_router)
    client = TestClient(app)
    resp = client.get("/media/photos/ocr")
    assert resp.status_code == 401
