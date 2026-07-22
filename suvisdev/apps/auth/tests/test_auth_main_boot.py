from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def test_healthz_ok(rsa_keypair):
    import auth_main

    client = TestClient(auth_main.app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_docs_disabled(rsa_keypair):
    import auth_main

    client = TestClient(auth_main.app)
    assert auth_main.app.docs_url is None
    assert client.get("/docs").status_code == 404
