"""profile 라우터 부분 수정(nickname / preferred_genres) + 소유권 가드 테스트.

`preferred_genres`는 UI 감사(§1 (f))에서 "프론트뿐 아니라 API 계약 자체가
없다"로 지적된 항목 — 2026-08-07에 기존 PATCH를 확장해 열었다.
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
from viewer.adapter.inbound.api.v1.profile_router import profile_router  # noqa: E402
from viewer.app.dtos.profile_dto import ProfileDto  # noqa: E402
from viewer.dependencies.profile_provider import get_profile_use_case  # noqa: E402


def _dto(*, nickname: str = "태기", genres: list[str] | None = None) -> ProfileDto:
    return ProfileDto(
        id=7,
        username="tester",
        nickname=nickname,
        email="t@example.com",
        gender="",
        preferred_genres=genres if genres is not None else [],
        providers=[],
    )


class _FakeProfileUseCase:
    def __init__(self) -> None:
        self.nickname_calls: list[tuple[int, str]] = []
        self.genre_calls: list[tuple[int, list[str]]] = []

    async def get_profile(self, user_id: int) -> ProfileDto | None:
        return _dto()

    async def update_nickname(self, user_id: int, nickname: str) -> ProfileDto | None:
        self.nickname_calls.append((user_id, nickname))
        return _dto(nickname=nickname)

    async def update_preferred_genres(
        self, user_id: int, genres: list[str]
    ) -> ProfileDto | None:
        self.genre_calls.append((user_id, genres))
        return _dto(genres=genres)


def _build_client(
    use_case: _FakeProfileUseCase, *, principal: UserPrincipal | None
) -> TestClient:
    app = FastAPI()
    app.include_router(profile_router)
    app.dependency_overrides[get_profile_use_case] = lambda: use_case
    if principal is not None:
        app.dependency_overrides[require_user] = lambda: principal
    return TestClient(app)


class ProfilePatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.use_case = _FakeProfileUseCase()
        self.client = _build_client(
            self.use_case, principal=UserPrincipal(user_id=7, username="tester")
        )

    def test_updates_preferred_genres_only(self) -> None:
        resp = self.client.patch("/profile/7", json={"preferred_genres": ["액션", "SF"]})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["preferred_genres"], ["액션", "SF"])
        self.assertEqual(self.use_case.genre_calls, [(7, ["액션", "SF"])])
        self.assertEqual(self.use_case.nickname_calls, [])

    def test_updates_nickname_only(self) -> None:
        resp = self.client.patch("/profile/7", json={"nickname": "새이름"})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.use_case.nickname_calls, [(7, "새이름")])
        self.assertEqual(self.use_case.genre_calls, [])

    def test_empty_genre_list_clears_preferences(self) -> None:
        """빈 배열은 '수정 항목 없음'이 아니라 '전체 해제'다."""
        resp = self.client.patch("/profile/7", json={"preferred_genres": []})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.use_case.genre_calls, [(7, [])])

    def test_blank_genre_strings_are_dropped(self) -> None:
        resp = self.client.patch("/profile/7", json={"preferred_genres": ["액션", "  ", ""]})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.use_case.genre_calls, [(7, ["액션"])])

    def test_no_fields_returns_400(self) -> None:
        resp = self.client.patch("/profile/7", json={})

        self.assertEqual(resp.status_code, 400)

    def test_too_many_genres_returns_422(self) -> None:
        resp = self.client.patch("/profile/7", json={"preferred_genres": ["장르"] * 21})

        self.assertEqual(resp.status_code, 422)
        self.assertEqual(self.use_case.genre_calls, [])


class ProfilePatchAuthTests(unittest.TestCase):
    def test_other_user_returns_403(self) -> None:
        use_case = _FakeProfileUseCase()
        client = _build_client(use_case, principal=UserPrincipal(user_id=7, username="tester"))

        resp = client.patch("/profile/1", json={"preferred_genres": ["액션"]})

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(use_case.genre_calls, [])

    def test_without_token_returns_401(self) -> None:
        use_case = _FakeProfileUseCase()
        client = _build_client(use_case, principal=None)

        resp = client.patch("/profile/7", json={"preferred_genres": ["액션"]})

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(use_case.genre_calls, [])


if __name__ == "__main__":
    unittest.main()
