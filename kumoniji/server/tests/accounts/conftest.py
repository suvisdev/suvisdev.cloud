"""계정 테스트는 실제 Postgres에 붙는다. 테스트마다 임시 DB를 만들고 끝나면 지운다.
로컬: kumoniji/.env의 KUMONIJI_TEST_DATABASE_URL(kumoniji-db). CI: postgres 서비스 컨테이너."""

import os
import uuid
from pathlib import Path

import httpx
import psycopg
import pytest
from argon2 import PasswordHasher

from kumoniji.accounts import db, google, passwords

from .helpers import CID, KEY, ORIGIN


def _admin_url() -> str:
    url = os.environ.get("KUMONIJI_TEST_DATABASE_URL")
    if not url:
        env = Path(__file__).resolve().parents[3] / ".env"
        for line in env.read_text().splitlines() if env.exists() else []:
            if line.startswith("KUMONIJI_TEST_DATABASE_URL="):
                url = line.split("=", 1)[1]
    if not url:
        pytest.fail("KUMONIJI_TEST_DATABASE_URL이 없음 — kumoniji/.env 또는 환경 변수")
    return url


@pytest.fixture
def database():
    admin = _admin_url()
    name = f"t_{uuid.uuid4().hex}"
    with psycopg.connect(admin, autocommit=True) as c:
        c.execute(f'CREATE DATABASE "{name}"')
    url = admin.rsplit("/", 1)[0] + "/" + name
    db.init(url)
    yield url
    db.close()
    with psycopg.connect(admin, autocommit=True) as c:
        c.execute(f'DROP DATABASE "{name}" WITH (FORCE)')


@pytest.fixture
def outbox(monkeypatch, database):
    monkeypatch.setenv("KUMONIJI_PUBLIC_ORIGIN", ORIGIN)
    monkeypatch.setenv("KUMONIJI_JWT_SECRET", "k" * 48)
    sent = []
    from kumoniji.accounts import service, sessions

    def capture(to, kind, path, lang="en"):
        sent.append({"to": to, "kind": kind, "path": path})

    monkeypatch.setattr(service.mail, "send", capture)
    monkeypatch.setattr(sessions.mail, "send", capture)
    clean = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text="")))
    orig = passwords.check
    monkeypatch.setattr(passwords, "check", lambda pw, e, n, client=None: orig(pw, e, n, clean))
    return sent


@pytest.fixture
def fast_hash(monkeypatch):
    monkeypatch.setattr(passwords, "PH", PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1))


@pytest.fixture
def google_keys(monkeypatch):
    monkeypatch.setenv("KUMONIJI_GOOGLE_CLIENT_ID", CID)
    monkeypatch.setenv("KUMONIJI_GOOGLE_CLIENT_SECRET", "s")

    class Jwks:
        def get_signing_key_from_jwt(self, token):
            return type("K", (), {"key": KEY.public_key()})()

    monkeypatch.setattr(google, "_jwks", Jwks())
