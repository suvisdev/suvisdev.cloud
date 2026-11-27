"""검증 9·10: 구글 로그인·계정 연결."""

import threading
import time
from urllib.parse import parse_qs, urlparse

import pytest

from kumoniji.accounts import db, google

from .helpers import CID, OTHER, PW, browser, id_token, login, run_flow, signed_up

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
    with db.tx() as cur:  # 주인이 비밀번호를 바꾸는 등으로 전 세션이 끊김
        cur.execute("UPDATE sessions SET revoked_at = now()")
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


def test_new_device_mail_after_google_uses_language_chosen_in_app(outbox, monkeypatch):
    """구글 리다이렉트는 앱이 머리글을 못 단다 — start의 lang이 콜백의 새 기기 메일 언어가 된다(브라우저 언어보다 먼저)."""
    from kumoniji.accounts import service

    langs = []
    monkeypatch.setattr(service.mail, "send", lambda to, kind, path, lang="en": langs.append((kind, lang)))
    run_flow(browser(), monkeypatch)  # 첫 기기
    second = browser()
    second.headers.update({"user-agent": "Other/2.0", "accept-language": "en-US"})
    run_flow(second, monkeypatch, path="/api/auth/google/start?lang=zh")
    assert langs == [("new_device", "zh")]


def test_config_gives_the_app_the_web_client_id_to_ask_google_for(monkeypatch):
    """앱 구글 로그인(11-27): 앱은 이 값으로 ID 토큰을 받고, 서버는 같은 값으로 aud를 검증한다(공개값)"""
    monkeypatch.setenv("KUMONIJI_GOOGLE_ANDROID", "1")
    c = browser()
    j = c.get("/api/auth/config").json()
    assert j["google"] is True and j["google_client"] == CID


def test_config_hides_app_google_until_the_android_client_is_registered(monkeypatch):
    """Android 클라이언트 등록 전엔 앱 버튼을 숨긴다 — 웹 구글 로그인은 그대로(리뷰 19차)"""
    monkeypatch.delenv("KUMONIJI_GOOGLE_ANDROID", raising=False)
    j = browser().get("/api/auth/config").json()
    assert j["google"] is True and j["google_client"] == ""


def test_app_google_login_accepts_each_id_token_once(outbox, google_keys):
    """앱(/google/app): 같은 ID 토큰을 다시 보내면 거절 — 새어 나간 토큰으로 세션을 또 받지 못하게(리뷰 5차)"""
    from fastapi.testclient import TestClient

    from kumoniji.api import app

    from .helpers import ORIGIN, id_token

    a = TestClient(app, base_url=ORIGIN, headers={"x-kumoniji-client": "app"})
    nonce = "n" * 24
    tok = id_token(nonce)
    assert a.post("/api/auth/google/app", json={"id_token": tok, "nonce": nonce}).status_code == 200
    assert a.post("/api/auth/google/app", json={"id_token": tok, "nonce": nonce}).status_code == 401
    # 같은 토큰을 다른 인코딩으로(서명 base64url 끝에 덧붙인 비트 등) 적어도 내용이 같으면 거절(리뷰 6차)
    h, p, sig = tok.split(".")
    padded = h + "." + p + "." + sig + "=="  # 일부 디코더가 허용하는 패딩
    assert a.post("/api/auth/google/app", json={"id_token": padded, "nonce": nonce}).status_code == 401
    again = id_token(nonce, iat=1)  # 같은 실행(같은 nonce)의 다음 로그인 — 새 토큰이면 된다
    assert a.post("/api/auth/google/app", json={"id_token": again, "nonce": nonce}).status_code == 200
