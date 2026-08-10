"""아바타 업로드 라우터 — 인증·MIME·크기 가드와 성공 경로 테스트.

대상 사용자를 토큰에서만 뽑으므로(경로·바디에 user_id 없음) IDOR 케이스가
따로 없다 — 대신 무인증 401을 확인한다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from shared.security.require_user import UserPrincipal, require_user  # noqa: E402
from viewer.adapter.inbound.api.v1.avatar_router import avatar_router  # noqa: E402
from viewer.app.dtos.profile_dto import ProfileDto  # noqa: E402
from viewer.dependencies.profile_provider import get_profile_use_case  # noqa: E402


class _FakeProfileUseCase:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, str, str]] = []

    async def get_profile(self, user_id: int) -> ProfileDto | None:
        return None

    async def update_nickname(self, user_id: int, nickname: str) -> ProfileDto | None:
        return None

    async def update_preferred_genres(
        self, user_id: int, genres: list[str]
    ) -> ProfileDto | None:
        return None

    async def upload_avatar(
        self, user_id: int, data: bytes, *, content_type: str, ext: str
    ) -> ProfileDto | None:
        self.calls.append((user_id, len(data), content_type, ext))
        return ProfileDto(
            id=user_id,
            username="tester",
            nickname="태기",
            email="t@example.com",
            gender="",
            avatar_key=f"avatars/{user_id}/abc.{ext}",
            avatar_url="https://example.com/signed",
        )


def _build_client(
    use_case: _FakeProfileUseCase, *, principal: UserPrincipal | None
) -> TestClient:
    app = FastAPI()
    app.include_router(avatar_router)
    app.dependency_overrides[get_profile_use_case] = lambda: use_case
    if principal is not None:
        app.dependency_overrides[require_user] = lambda: principal
    return TestClient(app)


class AvatarUploadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.use_case = _FakeProfileUseCase()
        self.client = _build_client(
            self.use_case, principal=UserPrincipal(user_id=7, username="tester")
        )

    def test_uploads_and_returns_presigned_url(self) -> None:
        resp = self.client.post(
            "/avatar/upload",
            files={"file": ("me.png", b"\x89PNG fake bytes", "image/png")},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["avatar_url"], "https://example.com/signed")
        self.assertEqual(resp.json()["avatar_key"], "avatars/7/abc.png")
        # user_id는 토큰에서, 확장자는 MIME에서 온다(파일명 "me.png"가 아니라).
        self.assertEqual(self.use_case.calls, [(7, 15, "image/png", "png")])

    def test_extension_comes_from_mime_not_filename(self) -> None:
        resp = self.client.post(
            "/avatar/upload",
            files={"file": ("evil.php.jpg", b"fake", "image/webp")},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.use_case.calls[0][3], "webp")

    def test_rejects_unsupported_mime_with_415(self) -> None:
        resp = self.client.post(
            "/avatar/upload",
            files={"file": ("doc.pdf", b"%PDF-", "application/pdf")},
        )

        self.assertEqual(resp.status_code, 415)
        self.assertEqual(self.use_case.calls, [])

    def test_rejects_oversized_image_with_413(self) -> None:
        oversized = b"x" * (5 * 1024 * 1024 + 1)
        resp = self.client.post(
            "/avatar/upload",
            files={"file": ("big.jpg", oversized, "image/jpeg")},
        )

        self.assertEqual(resp.status_code, 413)
        self.assertEqual(self.use_case.calls, [])

    def test_accepts_image_exactly_at_limit(self) -> None:
        at_limit = b"x" * (5 * 1024 * 1024)
        resp = self.client.post(
            "/avatar/upload",
            files={"file": ("big.jpg", at_limit, "image/jpeg")},
        )

        self.assertEqual(resp.status_code, 200)

    def test_rejects_empty_file_with_400(self) -> None:
        resp = self.client.post(
            "/avatar/upload",
            files={"file": ("empty.png", b"", "image/png")},
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.use_case.calls, [])


class AvatarUploadAuthTests(unittest.TestCase):
    def test_requires_login(self) -> None:
        client = _build_client(_FakeProfileUseCase(), principal=None)

        resp = client.post(
            "/avatar/upload",
            files={"file": ("me.png", b"fake", "image/png")},
        )

        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
