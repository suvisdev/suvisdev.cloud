"""키 비활성화·비밀 키 재발급 — 어드민 API로 바꾼 뒤 채점·검증이 실제로 따르는지 HTTP로 본다."""

from __future__ import annotations

import asyncio

import pytest
from fakes import (
    HUMAN,
    _FakeEventRepository,
    _FakeModel,
    _FakeRedis,
    _FakeSiteRepository,
    _FakeVelocity,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from shared.security.require_admin import AdminPrincipal, require_admin

from deolmi.adapter.inbound.api import deolmi_router
from deolmi.adapter.outbound.security.jwt_score_token_adapter import JwtScoreTokenAdapter
from deolmi.app.dtos.site_dto import SiteCreateCommand
from deolmi.app.use_cases.score_interactor import ScoreInteractor
from deolmi.app.use_cases.site_admin_interactor import SiteAdminInteractor
from deolmi.dependencies.deolmi_provider import get_score_use_case, get_site_admin_use_case


@pytest.fixture
def app():
    sites, events, model = _FakeSiteRepository(), _FakeEventRepository(), _FakeModel()
    score = ScoreInteractor(
        sites=sites,
        events=events,
        model=model,
        tokens=JwtScoreTokenAdapter("admin-test-secret", _FakeRedis()),
        velocity=_FakeVelocity(),
    )
    admin = SiteAdminInteractor(sites=sites, events=events, model=model)
    app = FastAPI()
    app.include_router(deolmi_router, prefix="/api")
    app.dependency_overrides[get_score_use_case] = lambda: score
    app.dependency_overrides[get_site_admin_use_case] = lambda: admin
    app.state.admin = admin
    return app


@pytest.fixture
def client(app):
    app.dependency_overrides[require_admin] = lambda: AdminPrincipal(user_id=1, username="admin")
    return TestClient(app)


@pytest.fixture
def issued(app):
    return asyncio.run(app.state.admin.create_site(SiteCreateCommand("고객", "free", ())))


def _score(client, site_key):
    return client.post("/api/deolmi/score", json={"site_key": site_key, "signals": HUMAN})


def _verify(client, secret, token):
    return client.post("/api/deolmi/verify", json={"secret": secret, "token": token})


def test_deactivate_stops_score_and_verify_then_activate_restores(client, issued):
    key, secret = issued.site.site_key, issued.secret_key
    token = _score(client, key).json()["token"]

    res = client.post(f"/api/deolmi/admin/sites/{key}/deactivate")
    assert res.status_code == 200
    assert res.json()["active"] is False
    assert _score(client, key).status_code == 401
    assert _verify(client, secret, token).status_code == 401

    res = client.post(f"/api/deolmi/admin/sites/{key}/activate")
    assert res.status_code == 200
    assert res.json()["active"] is True
    assert _score(client, key).status_code == 200
    assert _verify(client, secret, token).status_code == 200


def test_rotate_invalidates_old_secret_immediately_and_keeps_public_key(client, issued):
    key, old = issued.site.site_key, issued.secret_key
    token = _score(client, key).json()["token"]

    res = client.post(f"/api/deolmi/admin/sites/{key}/rotate-secret")
    assert res.status_code == 200
    body = res.json()
    assert body["site_key"] == key
    assert body["secret_key"].startswith("sk_") and body["secret_key"] != old
    assert "secret_hash" not in body

    assert _verify(client, old, token).status_code == 401
    assert _verify(client, body["secret_key"], token).status_code == 200


def test_rotate_on_deactivated_site_keeps_it_off(client, issued):
    key = issued.site.site_key
    client.post(f"/api/deolmi/admin/sites/{key}/deactivate")

    body = client.post(f"/api/deolmi/admin/sites/{key}/rotate-secret").json()

    assert body["active"] is False
    assert _score(client, key).status_code == 401


@pytest.mark.parametrize("action", ["deactivate", "activate", "rotate-secret"])
def test_unknown_site_is_404(client, action):
    assert client.post(f"/api/deolmi/admin/sites/pk_none/{action}").status_code == 404


@pytest.mark.parametrize("action", ["deactivate", "activate", "rotate-secret"])
def test_key_operations_require_admin(app, action):
    res = TestClient(app).post(f"/api/deolmi/admin/sites/pk_any/{action}")
    assert res.status_code == 401
