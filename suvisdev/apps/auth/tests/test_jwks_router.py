from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def test_jwks_returns_kid_and_no_private_material(rsa_keypair):
    import auth_main

    client = TestClient(auth_main.app)
    resp = client.get("/.well-known/jwks.json")
    assert resp.status_code == 200
    key = resp.json()["keys"][0]
    assert key["kid"] == "test-kid"
    assert key["alg"] == "RS256"
    assert "d" not in key
