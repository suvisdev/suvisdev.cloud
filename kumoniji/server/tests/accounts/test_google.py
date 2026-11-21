"""검증 9·10: 구글 로그인·계정 연결."""

import threading
import time
from urllib.parse import parse_qs, urlparse

import pytest

from kumoniji.accounts import db, google

from .helpers import OTHER, PW, browser, id_token, login, run_flow, signed_up

pytestmark = pytest.mark.usefixtures("google_keys")


def test_9_login_creates_account_and_session(outbox, monkeypatch):
    c = browser()
    r = run_flow(c, monkeypatch)
    assert r.headers["location"] == "/"
    assert c.post("/api/games").status_code == 200
    assert c.get("/api/auth/me").json()["providers"] == ["google"]


@pytest.mark.parametrize(
    "bad",
    [
        lambda n: id_token(n, key=OTHER),  # 다른 키로 서명
        lambda n: id_token(n, alg="HS256"),  # 허용 안 된 알고리즘
        lambda n: id_token(n, iss="https://evil.example"),
        lambda n: id_token(n, aud="someone-else"),
        lambda n: id_token("not-the-nonce"),
        lambda n: id_token(n, exp=int(time.time()) - 10),
    ],
)
def test_9_bad_id_tokens_are_rejected(outbox, monkeypatch, bad):
    c = browser()
    assert run_flow(c, monkeypatch, token_for=bad).headers["location"] == "/?auth_error=google"
    assert c.post("/api/games").status_code == 401


def test_9_wrong_state_or_missing_flow_cookie_is_rejected(outbox, monkeypatch):
    c = browser()
    assert run_flow(c, monkeypatch, state="forged").headers["location"] == "/?auth_error=google"
    stranger = browser()  # 흐름 쿠키 없이 콜백만 — 남이 만든 링크로 로그인시키기
    r = stranger.get("/api/auth/google/callback?code=abc&state=x", follow_redirects=False)
    assert r.headers["location"] == "/?auth_error=google"


def test_10_same_email_password_account_is_not_merged(outbox, fast_hash, monkeypatch):
    signed_up(browser(), outbox)  # me@x.com 자체 계정
    c = browser()
    run_flow(c, monkeypatch)
    me = c.get("/api/auth/me").json()
    assert me["email"] is None and me["providers"] == ["google"]  # 새 계정, 이메일 비움
    with db.tx() as cur:
        assert cur.execute("SELECT count(*) AS n FROM accounts").fetchone()["n"] == 2


def test_10_link_needs_recent_auth_and_unlink_keeps_last_method(outbox, fast_hash, monkeypatch):
    c = browser()
    signed_up(c, outbox)
    login(c)
    with db.tx() as cur:
        cur.execute("UPDATE sessions SET reauth_at = now() - interval '10 minutes'")
    assert c.get("/api/auth/google/start?link=true", follow_redirects=False).status_code == 403
    assert c.post("/api/auth/reauth", json={"password": PW}).status_code == 200
    assert run_flow(c, monkeypatch, link=True).headers["location"] == "/?linked=google"
    assert c.get("/api/auth/me").json()["providers"] == ["google"]
    assert c.post("/api/auth/google/unlink").status_code == 200  # 비밀번호가 있으니 해제 가능
    g = browser()
    run_flow(g, monkeypatch, token_for=lambda n: id_token(n, sub="g-only"))
    with db.tx() as cur:
        cur.execute("UPDATE sessions SET reauth_at = now()")
    assert g.post("/api/auth/google/unlink").status_code == 409  # 구글이 유일한 로그인 수단


def test_10_sub_already_linked_elsewhere_cannot_be_linked(outbox, fast_hash, monkeypatch):
    run_flow(browser(), monkeypatch)  # g-123으로 이미 계정 있음
    c = browser()
    signed_up(c, outbox, email="other@x.com")
    login(c, "other@x.com")
    assert run_flow(c, monkeypatch, link=True).headers["location"] == "/?auth_error=google"


def test_10_link_started_by_a_session_that_is_revoked_meanwhile_fails(outbox, fast_hash, monkeypatch):
    c = browser()
    signed_up(c, outbox)
    login(c)
    r = c.get("/api/auth/google/start?link=true", follow_redirects=False)  # 탈취된 세션이 연결을 시작
    q = parse_qs(urlparse(r.headers["location"]).query)
    browser_owner = browser()
    login(browser_owner)
    assert browser_owner.post("/api/auth/logout-all").status_code == 200  # 주인이 전부 로그아웃
    monkeypatch.setattr(google, "exchange", lambda code, verifier, origin, client=None: id_token(q["nonce"][0]))
    done = c.get(f"/api/auth/google/callback?code=abc&state={q['state'][0]}", follow_redirects=False)
    assert done.headers["location"] == "/?auth_error=google"
    with db.tx() as cur:
        assert cur.execute("SELECT count(*) AS n FROM identities").fetchone()["n"] == 0


def test_10_same_google_account_first_login_twice_at_once_makes_one_account(database):
    claims = {"sub": "g-race", "email": "race@example.com", "email_verified": True}
    first_inside, out = threading.Event(), []

    def one(wait):
        with db.tx() as c:
            if wait:
                first_inside.wait()
            out.append(google.find_or_create(c, claims))
            if not wait:
                first_inside.set()
                threading.Event().wait(0.5)  # 커밋 전에 두 번째가 들어온다

    ts = [threading.Thread(target=one, args=(False,)), threading.Thread(target=one, args=(True,))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert len(out) == 2 and out[0] == out[1]
