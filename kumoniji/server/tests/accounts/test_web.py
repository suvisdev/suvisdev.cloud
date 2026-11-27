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
    # 거부(실패 쪽으로 닫힘)는 그대로, 코드는 503 — 401(세션 끝남)이면 앱이 로그아웃된 줄 안다(앱 리뷰 45차)
    for r in (c.post("/api/games"), c.post("/api/auth/logout")):
        assert r.status_code == 503 and r.json()["detail"]["code"] == "busy"


def test_11_reused_refresh_over_http_revokes_every_session(outbox, fast_hash):
    signed_up(browser(), outbox)
    victim, thief = browser(), browser()
    login(victim)
    login(thief)
    stolen = victim.cookies.get("__Host-krt")
    assert victim.post("/api/auth/refresh").status_code == 200  # 주인이 먼저 회전
    with db.tx() as cur:  # 다시 받기(REPLAY) 구간이 지난 뒤
        cur.execute("UPDATE spent_refresh SET spent_at = now() - interval '26 minutes'")
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
    with db.tx() as c:  # 방금 회전은 응답을 못 받은 재시도로 보고 같은 토큰을 다시 주므로 시간을 지나게
        c.execute("UPDATE spent_refresh SET spent_at = now() - interval '26 minutes'")
    langs = []
    monkeypatch.setattr(sessions.mail, "send", lambda to, kind, path, lang="en": langs.append((kind, lang)))
    assert app_client.post("/api/auth/refresh", json={"refresh": old}).status_code == 401  # 재사용 → 전부 폐기
    assert langs == [("security", "zh")]


def test_web_lost_refresh_response_is_fetched_again_by_any_tab_of_the_same_browser(outbox, fast_hash):
    """웹 갱신 응답을 못 받아 옛 쿠키가 남아도, 같은 브라우저(재시도 쿠키가 같음)라면 다른 탭·새로고침이 30초 뒤
    다시 보내도 같은 새 토큰 — 전 세션 폐기가 아니다. 다른 브라우저(쿠키 탈취)는 기존대로 탐지(앱 리뷰 60·62차)."""
    signed_up(browser(), outbox)
    me, thief, other = browser(), browser(), browser()
    login(me)
    login(other)  # 다른 기기
    krk = me.cookies.get("__Host-krk")
    assert krk  # 로그인 응답이 심음 — 첫 갱신 전에 있다
    old = me.cookies.get("__Host-krt")
    first = me.post("/api/auth/refresh")
    assert first.status_code == 200
    new = first.cookies.get("__Host-krt")
    me.cookies.delete("__Host-krt")
    me.cookies.set("__Host-krt", old)  # 응답을 못 받았다 — 브라우저엔 옛 쿠키
    with db.tx() as cur:  # 동시 갱신 유예(30초)가 지난 뒤(다시 받기 구간 안)
        cur.execute("UPDATE spent_refresh SET spent_at = now() - interval '1 minute'")
    again = me.post("/api/auth/refresh")
    assert again.status_code == 200 and again.cookies.get("__Host-krt") == new
    assert other.get("/api/auth/me").status_code == 200  # 다른 기기 그대로
    thief.cookies.set("__Host-krt", old)  # 같은 옛 쿠키를 다른 브라우저에서
    assert thief.post("/api/auth/refresh").status_code == 401  # 옛 토큰엔 키를 주지 않음 → 탐지
    assert other.get("/api/auth/me").status_code == 401  # 탐지 → 전 세션 폐기


def test_web_tab_race_gets_no_new_token_so_stolen_cookies_cannot_follow_rotations(outbox, fast_hash):
    """웹 동시 갱신(30초 안·같은 IP)엔 새 토큰을 다시 주지 않고 409 — 쿠키(리프레시+키)를 함께 훔친 사람이 같은 IP에서
    회전마다 따라붙어도 토큰을 못 얻는다. 같은 브라우저의 탭은 먼저 받은 탭의 쿠키로 다시 보내면 된다(11-26 결정 3번)."""
    signed_up(browser(), outbox)
    me, thief = browser(), browser()
    login(me)
    old = me.cookies.get("__Host-krt")
    for k, v in me.cookies.items():
        thief.cookies.set(k, v)  # 쿠키를 통째로 훔침(같은 IP)
    thief.headers["x-csrf"] = me.headers["x-csrf"]
    assert me.post("/api/auth/refresh").status_code == 200  # 주인 탭 A가 먼저 회전
    r = thief.post("/api/auth/refresh")  # 같은 옛 쿠키로 30초 안
    assert r.status_code == 409 and "__Host-krt" not in r.cookies
    assert thief.cookies.get("__Host-krt") == old
    app = thief.post(  # 앱인 척(헤더·본문)해도 웹 키면 같다(리뷰)
        "/api/auth/refresh",
        headers={"x-kumoniji-client": "app"},
        json={"refresh": old, "retry": me.cookies.get("__Host-krk")},
    )
    assert app.status_code == 409 and "refresh" not in app.text
    assert me.post("/api/auth/refresh").status_code == 200  # 탭 B는 공유된 새 쿠키로 다시 — 그대로 된다


def test_retry_key_cookie_is_set_by_login_not_csrf_and_extended_with_the_same_value(outbox, fast_hash):
    """CSRF 받기는 키를 심지 않는다 — 두 탭이 동시에 받으면 서로 다른 키가 덮여 다시 받기가 탈취로 판정된다(33차 ①)."""
    c = browser()
    assert c.cookies.get("__Host-krk") is None  # browser()가 CSRF를 받았어도 없음
    signed_up(c, outbox)
    first = login(c).cookies.get("__Host-krk")
    assert first
    r = c.post("/api/auth/refresh")  # 갱신해도 같은 값, 기한만 늘림
    assert r.status_code == 200 and r.cookies.get("__Host-krk") == first and "Max-Age" in r.headers["set-cookie"]


def test_late_duplicate_refresh_response_does_not_log_out_after_access_expires(outbox, fast_hash):
    """같은 새 토큰 T1을 담은 응답이 둘 — 한 탭이 T1로 T2까지 회전한 뒤 늦은 T1 응답이 쿠키를 덮어도, 액세스가 끝난
    15분 뒤 T1로 오면 아직 안 쓰인 T2를 다시 받는다(로그아웃 아님, 33차 ②)."""
    signed_up(browser(), outbox)
    me = browser()
    login(me)
    t0 = me.cookies.get("__Host-krt")
    t1 = me.post("/api/auth/refresh").cookies.get("__Host-krt")  # 탭 A의 응답(늦게 도착할 것)
    t2 = me.post("/api/auth/refresh").cookies.get("__Host-krt")  # 탭 B가 T1 → T2
    assert len({t0, t1, t2}) == 3
    me.cookies.delete("__Host-krt")
    me.cookies.set("__Host-krt", t1)  # 늦은 응답이 쿠키를 T1로 덮음
    with db.tx() as cur:  # 액세스 수명(15분)이 지난 뒤
        cur.execute("UPDATE spent_refresh SET spent_at = now() - interval '16 minutes'")
    again = me.post("/api/auth/refresh")
    assert again.status_code == 200 and again.cookies.get("__Host-krt") == t2


def test_a_stolen_refresh_alone_cannot_get_the_retry_key(outbox, fast_hash):
    """키 쿠키 없이 온 갱신에 키만 심어 주는 길은 없다 — 리프레시만 훔친 사람은 키 없이 회전할 수밖에 없고, 주인의
    다음 갱신이 재사용으로 잡힌다(앱 리뷰 49·50차)."""
    signed_up(browser(), outbox)
    owner, thief = browser(), browser()
    login(owner)
    stolen = owner.cookies.get("__Host-krt")
    thief.cookies.set("__Host-krt", stolen)
    r = thief.post("/api/auth/refresh")
    assert r.status_code == 200  # 키 없이 그냥 회전 — 다시 받기 표시(키)가 없는 회전
    assert "__Host-krk" not in r.cookies  # 키 없이 온 갱신엔 키를 주지 않는다(53차)
    thief.cookies.set("__Host-krk", "wrong")
    assert "__Host-krk" not in thief.post("/api/auth/refresh").cookies  # 틀린 키여도
    with db.tx() as c:  # 방금(30초 안)이면 같은 브라우저의 동시 갱신(409)으로 본다 — 그 뒤에 온 주인
        c.execute("UPDATE spent_refresh SET spent_at = now() - interval '1 minute'")
    assert owner.post("/api/auth/refresh").status_code == 401  # 주인 쪽 갱신이 재사용으로 탐지


def test_a_non_ascii_retry_cookie_is_just_a_wrong_key(outbox, fast_hash):
    """재시도 키 쿠키에 비ASCII가 와도 500이 아니라 틀린 키처럼 — 회전은 되고 키는 안 준다(앱 리뷰 55차)."""
    signed_up(browser(), outbox)
    c = browser()
    login(c)
    jar = "; ".join(f"{k}={v}" for k, v in c.cookies.items() if k != "__Host-krk")
    r = c.post("/api/auth/refresh", headers={"cookie": f"{jar}; __Host-krk=caf\u00e9".encode()})
    assert r.status_code == 200
    assert "__Host-krk" not in r.cookies


def test_a_non_ascii_csrf_header_is_rejected_not_crashed(outbox, fast_hash):
    """CSRF 헤더에 비ASCII가 와도 500이 아니라 403(앱 리뷰 55차 — 같은 문자열 비교)."""
    signed_up(browser(), outbox)
    c = browser()
    login(c)
    assert c.post("/api/auth/logout", headers={"x-csrf": "café".encode()}).status_code == 403


def test_session_list_api_is_gone(outbox, fast_hash):
    """기기 목록·개별 종료 API는 화면이 없어 뺐다(11-26 사용자) — 로그인해도 없어야 한다."""
    c = browser()
    signed_up(c, outbox)
    login(c, "ME@X.com")
    assert c.get("/api/auth/sessions").status_code == 404
    assert c.delete("/api/auth/sessions/00000000-0000-0000-0000-000000000000").status_code in (404, 405)
