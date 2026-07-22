from __future__ import annotations

import base64
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mova.adapter.inbound.api.v1 import whoami_router as whoami_router_module  # noqa: E402
from mova.adapter.inbound.api.v1.whoami_router import whoami_router  # noqa: E402


@pytest.fixture()
def rsa_keypair(monkeypatch) -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    monkeypatch.setenv("JWT_PUBLIC_KEY_B64", base64.b64encode(public_pem.encode()).decode())
    return private_pem, public_pem


def _issue(private_pem: str, *, aud: str = "suvis-mova", roles: list[str] | None = None) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": "1",
            "roles": roles if roles is not None else ["user"],
            "aud": aud,
            "iat": now,
            "exp": now + timedelta(minutes=10),
            "jti": "test-jti",
        },
        private_pem,
        algorithm="RS256",
    )


@pytest.fixture()
def client(monkeypatch):
    async def _fake_get_viewer_user_nicknames(user_ids):
        return {1: "테스트유저"} if 1 in user_ids else {}

    monkeypatch.setattr(
        whoami_router_module, "get_viewer_user_nicknames", _fake_get_viewer_user_nicknames
    )
    app = FastAPI()
    app.include_router(whoami_router)
    return TestClient(app)


def test_whoami_returns_claims_with_valid_token(client, rsa_keypair):
    private_pem, _ = rsa_keypair
    token = _issue(private_pem)
    resp = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {
        "sub": "1",
        "roles": ["user"],
        "aud": "suvis-mova",
        "username": "테스트유저",
    }


def test_whoami_username_falls_back_to_empty_when_not_found(client, rsa_keypair, monkeypatch):
    async def _fake_empty(user_ids):
        return {}

    monkeypatch.setattr(whoami_router_module, "get_viewer_user_nicknames", _fake_empty)
    private_pem, _ = rsa_keypair
    token = _issue(private_pem)
    resp = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == ""


def test_whoami_without_token_returns_401(client):
    resp = client.get("/whoami")
    assert resp.status_code == 401


def test_whoami_wrong_role_returns_403(client, rsa_keypair):
    private_pem, _ = rsa_keypair
    token = _issue(private_pem, roles=["guest"])
    resp = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
