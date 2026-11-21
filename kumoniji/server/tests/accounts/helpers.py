import time
from urllib.parse import parse_qs, urlparse

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from kumoniji.accounts import db, google
from kumoniji.api import app

ORIGIN = "https://testserver"
PW, PW2 = "correct horse battery", "another long passphrase"
CID = "test-client.apps.googleusercontent.com"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_account(email="a@x.com", nickname="nick", verified=True) -> int:
    with db.tx() as c:
        return c.execute(
            """INSERT INTO accounts (email, email_key, nickname, verified_at)
               VALUES (%s, lower(%s), %s, CASE WHEN %s THEN now() END) RETURNING id""",
            (email, email, nickname, verified),
        ).fetchone()["id"]


def browser() -> TestClient:
    c = TestClient(app, base_url=ORIGIN)
    token = c.get("/api/auth/csrf").json()["csrf"]
    c.headers.update({"origin": ORIGIN, "x-csrf": token})
    return c


def token_of(m: dict) -> str:
    return parse_qs(urlparse(m["path"]).query)["token"][0]


def signed_up(c, outbox, email="me@x.com", nick="me") -> None:
    assert c.post("/api/auth/signup", json={"email": email, "password": PW, "nickname": nick}).status_code == 202
    assert c.post("/api/auth/verify", json={"token": token_of(outbox[-1]), "password": PW}).status_code == 200


def login(c, email="me@x.com", pw=PW):
    return c.post("/api/auth/login", json={"email": email, "password": pw})


def id_token(nonce, key=KEY, alg="RS256", **over):
    claims = {
        "iss": "https://accounts.google.com",
        "aud": CID,
        "sub": "g-123",
        "email": "me@x.com",
        "email_verified": True,
        "nonce": nonce,
        "exp": int(time.time()) + 300,
        "given_name": "Me",
    } | over
    return jwt.encode(claims, key if alg != "HS256" else "secret" * 8, alg)


def run_flow(c: TestClient, monkeypatch, token_for=lambda nonce: id_token(nonce), link=False, state=None, path=None):
    path = path or f"/api/auth/google/start{'?link=true' if link else ''}"
    r = c.get(path, follow_redirects=False)
    assert r.status_code == 302
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert q["code_challenge_method"] == ["S256"] and q["redirect_uri"] == [f"{ORIGIN}/api/auth/google/callback"]
    monkeypatch.setattr(google, "exchange", lambda code, verifier, origin, client=None: token_for(q["nonce"][0]))
    return c.get(f"/api/auth/google/callback?code=abc&state={state or q['state'][0]}", follow_redirects=False)
