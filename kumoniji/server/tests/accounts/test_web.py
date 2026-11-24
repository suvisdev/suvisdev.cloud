"""HTTP로 본 계정 흐름 — 검증 1·4·5·12·13·26 (실제 Postgres, 메일·HIBP는 가짜)."""

import statistics
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from kumoniji.accounts import db, mail
from kumoniji.api import app

from .helpers import ORIGIN, PW, PW2, browser, login, signed_up, token_of


def test_1_signup_verify_login_then_play(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    assert c.post("/api/games").status_code == 401  # 로그인 전
    r = login(c, "ME@X.com")
    assert r.status_code == 200 and "access" not in r.json()  # 웹은 토큰을 본문에 두지 않는다
    assert c.post("/api/games").status_code == 200
    assert c.get("/api/auth/me").json()["email"] == "me@x.com"


def test_13_cookie_attributes(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    cookies = [v for k, v in login(c).headers.multi_items() if k == "set-cookie"]
    for name in ("__Host-kat", "__Host-krt"):
        low = next(x for x in cookies if x.startswith(name + "=")).lower()
        assert "httponly" in low and "secure" in low and "samesite=lax" in low and "path=/" in low
        assert "domain=" not in low


def test_26_cookie_requests_need_origin_and_csrf(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    assert c.post("/api/games", headers={"origin": "https://evil.example"}).status_code == 403
    assert c.post("/api/games", headers={"x-csrf": "wrong"}).status_code == 403
    assert (
        c.post("/api/auth/login", json={"email": "me@x.com", "password": PW}, headers={"origin": "null"}).status_code
        == 403
    )
    assert c.post("/api/games").status_code == 200


def test_1_unverified_account_gets_no_session(outbox, fast_hash):
    c = browser()
    c.post("/api/auth/signup", json={"email": "me@x.com", "password": PW, "nickname": "me"})
    r = login(c)
    assert r.status_code == 200 and r.json()["verified"] is False
    assert c.post("/api/games").status_code == 401


def test_1_concurrent_case_variant_signups_make_one_account(outbox, fast_hash):
    def go(email):
        return browser().post("/api/auth/signup", json={"email": email, "password": PW, "nickname": "me"}).status_code

    with ThreadPoolExecutor(4) as ex:
        assert set(ex.map(go, ["A@x.com", "a@X.com", "a@x.com", "A@X.COM"])) == {202}
    with db.tx() as c:
        assert c.execute("SELECT count(*) AS n FROM accounts").fetchone()["n"] == 1


def test_1_preempted_signup_is_reclaimed_by_the_real_owner(outbox, fast_hash):
    attacker = browser()
    attacker.post("/api/auth/signup", json={"email": "victim@x.com", "password": PW, "nickname": "evil"})
    # 주인은 자기 메일함에 온 링크로만 인증할 수 있고, 그때 자기 비밀번호를 정한다
    owner = browser()
    owner.post("/api/auth/signup", json={"email": "victim@x.com", "password": PW2, "nickname": "owner"})
    assert owner.post("/api/auth/verify", json={"token": token_of(outbox[-1]), "password": PW2}).status_code == 200
    assert login(attacker, "victim@x.com", PW).status_code == 401
    assert login(owner, "victim@x.com", PW2).status_code == 200


def test_1_verified_address_signup_only_mails_the_owner(outbox, fast_hash):
    signed_up(browser(), outbox)
    r = browser().post("/api/auth/signup", json={"email": "me@x.com", "password": PW2, "nickname": "xx"})
    assert r.status_code == 202 and outbox[-1]["kind"] == "already"
    assert login(browser(), pw=PW2).status_code == 401


def test_4_same_response_whether_or_not_the_account_exists(outbox):
    signed_up(browser(), outbox)
    bodies, times = {"yes": set(), "no": set()}, {"yes": [], "no": []}
    for i in range(12):
        for who, email in (("yes", "me@x.com"), ("no", f"ghost{i}@x.com")):
            t = time.perf_counter()
            r = login(browser(), email, PW2)
            times[who].append(time.perf_counter() - t)
            bodies[who].add((r.status_code, r.text))
        with db.tx() as cur:  # 지연에 걸리지 않게 실패 기록은 매번 지운다
            cur.execute("DELETE FROM attempts")
    assert bodies["yes"] == bodies["no"] == {(401, '{"detail":{"code":"credentials"}}')}
    assert abs(statistics.median(times["yes"]) - statistics.median(times["no"])) < 0.05
    a = browser().post("/api/auth/reset/request", json={"email": "me@x.com"})
    b = browser().post("/api/auth/reset/request", json={"email": "ghost@x.com"})
    assert (a.status_code, a.text) == (b.status_code, b.text)


def test_4_sixth_failure_waits(outbox, fast_hash):
    signed_up(browser(), outbox)
    assert [login(browser(), pw=PW2).status_code for _ in range(6)] == [401] * 5 + [429]


def test_5_reset_kills_sessions_and_does_not_log_in(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    browser().post("/api/auth/reset/request", json={"email": "me@x.com"})
    tok = token_of(outbox[-1])
    other = browser()
    assert other.get(f"/api/auth/reset/check?token={tok}").json() == {"valid": True}
    assert other.get(f"/api/auth/reset/check?token={tok}").json() == {"valid": True}  # GET은 소비 안 함
    assert other.post("/api/auth/reset", json={"token": tok, "password": PW2}).status_code == 200
    assert other.cookies.get("__Host-kat") is None  # 자동 로그인 없음
    assert c.post("/api/games").status_code == 401  # 기존 세션 폐기
    assert other.post("/api/auth/reset", json={"token": tok, "password": PW}).status_code == 422  # 재사용
    assert outbox[-1]["kind"] == "password_changed"
    assert login(browser(), pw=PW2).status_code == 200


def test_5_reset_link_origin_is_fixed_even_with_a_forged_host(outbox, fast_hash):
    signed_up(browser(), outbox)
    browser().post("/api/auth/reset/request", json={"email": "me@x.com"}, headers={"host": "evil.example"})
    m = outbox[-1]
    body = mail.compose(m["to"], m["kind"], m["path"]).get_content()
    assert f"{ORIGIN}/reset?token=" in body and "evil.example" not in body


def test_5_reset_token_expires_after_30_minutes(outbox, fast_hash):
    signed_up(browser(), outbox)
    browser().post("/api/auth/reset/request", json={"email": "me@x.com"})
    with db.tx() as cur:
        cur.execute("UPDATE auth_tokens SET expires_at = now() - interval '1 second' WHERE purpose = 'reset'")
    assert browser().post("/api/auth/reset", json={"token": token_of(outbox[-1]), "password": PW2}).status_code == 422


def test_12_logout_is_immediate_and_refresh_rotates(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    old = c.cookies.get("__Host-krt")
    assert c.post("/api/auth/refresh").status_code == 200
    assert c.cookies.get("__Host-krt") != old
    assert c.post("/api/auth/logout").status_code == 200
    assert c.get("/api/auth/me").status_code == 401


def test_app_client_uses_bearer_without_csrf(outbox, fast_hash):
    signed_up(browser(), outbox)
    app_client = TestClient(app, base_url=ORIGIN, headers={"x-kumoniji-client": "app"})
    r = login(app_client).json()
    assert app_client.post("/api/games", headers={"authorization": f"Bearer {r['access']}"}).status_code == 200
    r2 = app_client.post("/api/auth/refresh", json={"refresh": r["refresh"]}).json()
    assert r2["refresh"] != r["refresh"]


def test_12_db_outage_fails_closed(outbox, fast_hash, monkeypatch):
    c = browser()
    signed_up(c, outbox)
    login(c)

    def down():
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "tx", down)
    assert c.post("/api/games").status_code == 401


def test_11_reused_refresh_over_http_revokes_every_session(outbox, fast_hash):
    signed_up(browser(), outbox)
    victim, thief = browser(), browser()
    login(victim)
    login(thief)
    stolen = victim.cookies.get("__Host-krt")
    assert victim.post("/api/auth/refresh").status_code == 200  # 주인이 먼저 회전
    with db.tx() as cur:  # 동시 갱신 유예(30초)가 지난 뒤
        cur.execute("UPDATE spent_refresh SET spent_at = now() - interval '1 minute'")
    thief.cookies.set("__Host-krt", stolen)
    assert thief.post("/api/auth/refresh").status_code == 401  # 회전된 토큰 재사용 → 탐지
    assert victim.get("/api/auth/me").status_code == 401  # 폐기가 커밋돼 모든 세션이 끝남
    assert thief.get("/api/auth/me").status_code == 401


def test_26_second_tab_keeps_the_same_csrf_value(outbox, fast_hash):
    first = browser()
    signed_up(first, outbox)
    login(first)
    again = first.get("/api/auth/csrf").json()["csrf"]  # 같은 브라우저의 다른 탭이 시작
    assert again == first.headers["x-csrf"]
    assert first.post("/api/games").status_code == 200


def test_4_app_clients_are_not_asked_for_captcha_but_still_slowed(outbox, fast_hash):
    signed_up(browser(), outbox)
    with db.tx() as cur:  # 이 IP에서 이미 실패가 많음(공유 IP)
        cur.execute("INSERT INTO attempts (key, fails) VALUES ('ip:testclient', 12)")
    assert login(browser()).json()["detail"]["code"] == "captcha"  # 웹은 사람 확인
    app_client = TestClient(app, base_url=ORIGIN, headers={"x-kumoniji-client": "app"})
    assert login(app_client).status_code == 200  # 앱은 확인 없이(지연이 없으면) 로그인


def test_reused_refresh_security_mail_uses_request_language(outbox, fast_hash, monkeypatch):
    from kumoniji.accounts import sessions

    signed_up(browser(), outbox)
    app_client = TestClient(app, base_url=ORIGIN, headers={"x-kumoniji-client": "app", "accept-language": "zh"})
    old = login(app_client).json()["refresh"]
    assert app_client.post("/api/auth/refresh", json={"refresh": old}).status_code == 200
    with db.tx() as c:  # 방금 회전은 다른 탭의 동시 갱신(409)으로 보므로 시간을 지나게
        c.execute("UPDATE spent_refresh SET spent_at = now() - interval '1 minute'")
    langs = []
    monkeypatch.setattr(sessions.mail, "send", lambda to, kind, path, lang="en": langs.append((kind, lang)))
    assert app_client.post("/api/auth/refresh", json={"refresh": old}).status_code == 401  # 재사용 → 전부 폐기
    assert langs == [("security", "zh")]
