"""mova·길들 점검 모드 — 경로 판별, 캐시·실패 시 막지 않음, 공개 조회, 관리자 토글."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from shared.security.require_admin import AdminPrincipal, require_admin  # noqa: E402

from viewer.adapter.inbound.api.v1 import admin_ops_router as ops_mod  # noqa: E402
from viewer.adapter.inbound.api.v1.admin_ops_router import admin_ops_router  # noqa: E402
from viewer.adapter.inbound.api.v1.maintenance_router import maintenance_router  # noqa: E402
from viewer.adapter.outbound.pg import maintenance_pg_repository as repo  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    repo._cache = None


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/mova", "mova"),
        ("/mova/chat", "mova"),
        ("/mova/whoami", None),  # 메인 사이트 로그인이 쓴다
        ("/movaxyz", None),
        ("/api/gildle/walks", "gildle"),
        ("/api/gildlex", None),
        ("/viewer/maintenance", None),
        ("/api/titanic/x", None),
    ],
)
def test_service_for_path(path: str, expected: str | None) -> None:
    assert repo.maintenance_service_for(path) == expected


class _FakeResult:
    def __init__(self, rows: list[tuple[str, bool]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[str, bool]]:
        return self._rows


class _FakeSession:
    def __init__(self, rows: list[tuple[str, bool]], calls: list[Any]) -> None:
        self._rows = rows
        self._calls = calls

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        self._calls.append(params)
        return _FakeResult(self._rows)

    async def commit(self) -> None:
        return None


def _fake_db(monkeypatch: pytest.MonkeyPatch, rows: list[tuple[str, bool]]) -> list[Any]:
    calls: list[Any] = []
    monkeypatch.setattr(
        repo, "get_viewer_session_factory", lambda: lambda: _FakeSession(rows, calls)
    )
    return calls


def test_load_reads_rows_and_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _fake_db(monkeypatch, [("mova", True), ("unknown", True)])
    assert asyncio.run(repo.load_maintenance()) == {"mova": True, "gildle": False}
    asyncio.run(repo.load_maintenance())
    assert len(calls) == 1  # 두 번째는 캐시
    asyncio.run(repo.load_maintenance(fresh=True))
    assert len(calls) == 2


def test_load_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken() -> Any:
        raise RuntimeError("relation site_maintenance does not exist")

    monkeypatch.setattr(repo, "get_viewer_session_factory", broken)
    assert asyncio.run(repo.load_maintenance()) == {"mova": False, "gildle": False}


def test_set_rejects_unknown_service() -> None:
    with pytest.raises(ValueError):
        asyncio.run(repo.set_maintenance("arda", True, "a"))


def test_public_status(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(*, fresh: bool = False) -> dict[str, bool]:
        return {"mova": False, "gildle": True}

    app = FastAPI()
    app.include_router(maintenance_router)
    import viewer.adapter.inbound.api.v1.maintenance_router as public_mod

    monkeypatch.setattr(public_mod, "load_maintenance", fake)
    assert TestClient(app).get("/maintenance").json() == {"mova": False, "gildle": True}


def _admin_client() -> TestClient:
    app = FastAPI()
    app.include_router(admin_ops_router)
    app.dependency_overrides[require_admin] = lambda: AdminPrincipal(user_id=1, username="a")
    return TestClient(app)


def test_toggle_requires_admin() -> None:
    app = FastAPI()
    app.include_router(admin_ops_router)
    res = TestClient(app).post("/admin/ops/maintenance/mova", json={"on": True})
    assert res.status_code == 401


def test_toggle_writes_and_returns_state(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, bool, str]] = []

    async def fake(service: str, enabled: bool, updated_by: str) -> dict[str, bool]:
        calls.append((service, enabled, updated_by))
        return {"mova": enabled, "gildle": False}

    monkeypatch.setattr(ops_mod, "set_maintenance", fake)
    res = _admin_client().post("/admin/ops/maintenance/mova", json={"on": True})
    assert res.status_code == 200
    assert res.json() == {"mova": True, "gildle": False}
    assert calls == [("mova", True, "a")]


def test_toggle_rejects_unknown_service(monkeypatch: pytest.MonkeyPatch) -> None:
    res = _admin_client().post("/admin/ops/maintenance/arda", json={"on": True})
    assert res.status_code == 422


def test_toggle_db_failure_is_503(monkeypatch: pytest.MonkeyPatch) -> None:
    async def broken(service: str, enabled: bool, updated_by: str) -> dict[str, bool]:
        raise RuntimeError("no table")

    monkeypatch.setattr(ops_mod, "set_maintenance", broken)
    res = _admin_client().post("/admin/ops/maintenance/gildle", json={"on": False})
    assert res.status_code == 503
