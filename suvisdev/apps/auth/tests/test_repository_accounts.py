"""UserRepository 계정 규칙(2026-10-20 리뷰) — 인메모리 SQLite로 실제 쿼리를 돌린다.

- admins 로그인 주체는 음수 sub(users.id와 충돌 없음)
- users에 같은 username이 있어도 admins 로그인이 막히지 않음 / 가입은 admins 아이디를 거부
- refresh 재확인용 find_by_subject
- 카카오 닉네임이 기존 username과 겹쳐도 가입이 깨지지 않음
"""

from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from auth import repository as module
from auth.rbac import Role
from auth.repository import (
    AdminMirror,
    AuthMirrorBase,
    GroupMirror,
    UserMirror,
    UsernameAlreadyExists,
    UserRepository,
)


@compiles(JSONB, "sqlite")
def _jsonb_as_json(_type: Any, _compiler: Any, **_kw: Any) -> str:
    return "JSON"


class _AsyncSessionShim:
    """repository가 쓰는 AsyncSession 메서드만 동기 Session으로 감싼다."""

    def __init__(self, session: Session) -> None:
        self._s = session

    async def execute(self, stmt: Any) -> Any:
        return self._s.execute(stmt)

    def add(self, obj: Any) -> None:
        self._s.add(obj)

    async def flush(self) -> None:
        self._s.flush()

    async def commit(self) -> None:
        self._s.commit()

    async def rollback(self) -> None:
        self._s.rollback()

    async def refresh(self, obj: Any) -> None:
        self._s.refresh(obj)


def _sha(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


@pytest.fixture()
def repo(monkeypatch) -> UserRepository:
    engine = create_engine("sqlite://")
    AuthMirrorBase.metadata.create_all(engine)  # 테스트 전용 인메모리 DB — 운영 DDL 아님
    with engine.begin() as conn:  # 운영 users.username UNIQUE 제약 재현(미러 ORM엔 없음)
        conn.execute(text("CREATE UNIQUE INDEX ux_users_username ON users (username)"))
    with Session(engine) as s:
        s.add_all([GroupMirror(id=1, code="admin"), GroupMirror(id=2, code="user")])
        s.add(
            AdminMirror(
                id=1, group_id=1, username="boss", password_hash=_sha("admin-pw"), email="b@x"
            )
        )
        s.add(
            UserMirror(
                id=1,
                group_id=2,
                username="someone",
                password_hash=_sha("user-pw"),
                email="s@x",
                nickname="someone",
                gender="undisclosed",
                preferred_genres=[],
                bio="",
            )
        )
        s.commit()

    @asynccontextmanager
    async def _session():
        with Session(engine, expire_on_commit=False) as s:
            yield _AsyncSessionShim(s)

    monkeypatch.setattr(module, "get_viewer_session_factory", lambda: _session)
    return UserRepository()


@pytest.mark.asyncio
async def test_admin_login_subject_never_equals_a_users_id(repo):
    admin = await repo.find_by_credentials("boss", "admin-pw")
    assert admin is not None and admin.roles == [Role.ADMIN]
    assert admin.user_id == -1  # admins.id=1 ↔ users.id=1과 겹치지 않음


@pytest.mark.asyncio
async def test_find_by_subject_resolves_admin_and_user_and_missing(repo):
    admin = await repo.find_by_subject("-1")
    assert admin is not None and admin.roles == [Role.ADMIN]
    user = await repo.find_by_subject("1")
    assert user is not None and user.username == "someone" and user.roles == [Role.USER]
    assert await repo.find_by_subject("999") is None
    assert await repo.find_by_subject("-999") is None


@pytest.mark.asyncio
async def test_signup_rejects_username_taken_by_admin(repo):
    with pytest.raises(UsernameAlreadyExists):
        await repo.create_user(email="new@x", password="pw-123456", username="boss")


@pytest.mark.asyncio
async def test_users_row_with_admin_username_does_not_block_admin_login(repo, monkeypatch):
    """가입 검사 도입 전에 이미 생긴 충돌 행이 있어도 관리자는 로그인된다."""
    engine_session = module.get_viewer_session_factory()
    async with engine_session() as s:
        s.add(
            UserMirror(
                group_id=2,
                username="boss",
                password_hash=_sha("attacker-pw"),
                email="evil@x",
                nickname="boss",
                gender="undisclosed",
                preferred_genres=[],
                bio="",
            )
        )
        await s.commit()

    admin = await repo.find_by_credentials("boss", "admin-pw")
    assert admin is not None and admin.user_id == -1 and admin.roles == [Role.ADMIN]
    attacker = await repo.find_by_credentials("boss", "attacker-pw")
    assert attacker is not None and attacker.user_id > 0 and attacker.roles == [Role.USER]


@pytest.mark.asyncio
async def test_kakao_nickname_colliding_with_existing_username_gets_unique_username(repo):
    created = await repo.find_or_create_by_kakao(
        provider_user_id="k-1", email=None, nickname="someone"
    )
    assert created.username != "someone" and created.username.startswith("someone_")

    fresh = await repo.find_or_create_by_kakao(provider_user_id="k-2", email=None, nickname="새닉")
    assert fresh.username == "새닉"  # 겹치지 않으면 닉네임 그대로


@pytest.mark.asyncio
async def test_kakao_signup_retries_once_when_username_taken_concurrently(repo, monkeypatch):
    """확인 시점엔 비어 있었지만 INSERT 직전에 다른 가입이 같은 username을 가져간 경우(레이스)."""

    async def _never_taken(_session: Any, _username: str) -> bool:
        return False

    monkeypatch.setattr(module, "_username_taken", _never_taken)
    created = await repo.find_or_create_by_kakao(
        provider_user_id="k-race", email=None, nickname="someone"
    )
    assert created.username.startswith("someone_")
    again = await repo.find_or_create_by_kakao(
        provider_user_id="k-race", email=None, nickname="someone"
    )
    assert again.user_id == created.user_id  # identity도 정상 저장됨
