"""라우터 오류 매핑과 공개 CORS — 실제 main.py와 같은 미들웨어 순서로 조립한다."""

from __future__ import annotations

import pytest
from fakes import (
    BOT,
    HUMAN,
    _FakeEventRepository,
    _FakeModel,
    _FakeSiteRepository,
    _FakeVelocity,
    make_site,
)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from deolmi.adapter.inbound.api import deolmi_router
from deolmi.adapter.inbound.api.public_cors import DeolmiPublicCorsMiddleware
from deolmi.adapter.outbound.security.jwt_score_token_adapter import JwtScoreTokenAdapter
from deolmi.app.use_cases.score_interactor import ScoreInteractor
from deolmi.dependencies import deolmi_provider
from deolmi.dependencies.deolmi_provider import get_score_use_case

FOREIGN = "https://ticket.example.com"


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://suvisdev.cloud"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(DeolmiPublicCorsMiddleware)
    app.include_router(deolmi_router, prefix="/api")
    use_case = ScoreInteractor(
        sites=_FakeSiteRepository(
            make_site(), make_site("pk_locked", domains=("ticket.example.com",))
        ),
        events=_FakeEventRepository(),
        model=_FakeModel(),
        tokens=JwtScoreTokenAdapter("router-secret"),
        velocity=_FakeVelocity(),
    )
    app.dependency_overrides[get_score_use_case] = lambda: use_case
    return TestClient(app)


def _preflight(client, path):
    return client.options(
        path,
        headers={
            "Origin": FOREIGN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_score_preflight_open_to_customer_sites(client):
    r = _preflight(client, "/api/deolmi/score")
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "*"


def test_other_paths_keep_global_cors(client):
    assert _preflight(client, "/api/deolmi/verify").status_code == 400


def test_score_then_verify_over_http(client):
    r = client.post(
        "/api/deolmi/score",
        json={"site_key": "pk_test", "signals": BOT},
        headers={"Origin": FOREIGN},
    )
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "*"
    assert r.json()["verdict"] == "block"
    v = client.post("/api/deolmi/verify", json={"secret": "sk_test", "token": r.json()["token"]})
    assert v.status_code == 200 and v.json()["decided_by"] == "rule"
    again = client.post(
        "/api/deolmi/verify", json={"secret": "sk_test", "token": r.json()["token"]}
    )
    assert again.status_code == 400


@pytest.mark.parametrize(
    ("body", "headers", "status"),
    [
        ({"site_key": "pk_nope", "signals": HUMAN}, {}, 401),
        ({"site_key": "pk_locked", "signals": HUMAN}, {"Origin": "https://evil.com"}, 403),
        ({"site_key": "pk_locked", "signals": HUMAN}, {}, 403),
        ({"site_key": "pk_test", "signals": {**HUMAN, "straightness": 2}}, {}, 422),
    ],
)
def test_score_errors(client, body, headers, status):
    assert client.post("/api/deolmi/score", json=body, headers=headers).status_code == status


def test_verify_errors(client):
    token = client.post("/api/deolmi/score", json={"site_key": "pk_test", "signals": HUMAN}).json()[
        "token"
    ]
    assert (
        client.post("/api/deolmi/verify", json={"secret": "sk_bad", "token": token}).status_code
        == 401
    )
    assert (
        client.post("/api/deolmi/verify", json={"secret": "sk_test", "token": "x.y.z"}).status_code
        == 401
    )


def test_unknown_signal_keys_are_dropped(client):
    r = client.post(
        "/api/deolmi/score", json={"site_key": "pk_test", "signals": {**HUMAN, "typed": "pw"}}
    )
    assert r.status_code == 200


def test_admin_routes_require_admin(client):
    assert client.get("/api/deolmi/admin/sites").status_code == 401
    assert client.post("/api/deolmi/admin/sites", json={"name": "x"}).status_code == 401


def test_sdk_is_served(client):
    r = client.get("/api/deolmi/sdk.js")
    assert r.status_code == 200 and "Deolmi" in r.text


def test_missing_token_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("DEOLMI_TOKEN_SECRET", raising=False)
    with pytest.raises(HTTPException) as e:
        deolmi_provider._tokens()
    assert e.value.status_code == 503
