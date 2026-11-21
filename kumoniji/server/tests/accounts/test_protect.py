"""검증 6: 주소 변경·새 기기 알림·보호 링크."""

from .helpers import PW, PW2, browser, login, signed_up, token_of


def test_6_new_device_login_mails_a_protect_link(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)  # 첫 기기 — 알림 없음
    assert outbox[-1]["kind"] != "new_device"
    browser().post("/api/auth/login", json={"email": "me@x.com", "password": PW}, headers={"user-agent": "phone"})
    assert outbox[-1]["kind"] == "new_device" and outbox[-1]["path"].startswith("/protect?token=")


def test_6_email_change_needs_new_address_confirmation(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    assert c.post("/api/auth/email", json={"email": "new@x.com"}).status_code == 202
    m = outbox[-1]
    assert m["to"] == "new@x.com" and m["kind"] == "email_confirm"
    assert c.get("/api/auth/me").json()["email"] == "me@x.com"  # 확인 전엔 그대로
    assert browser().post("/api/auth/email/confirm", json={"token": token_of(m)}).status_code == 200
    assert outbox[-1]["to"] == "me@x.com" and outbox[-1]["kind"] == "email_changed"
    assert login(browser(), "new@x.com").status_code == 200
    assert login(browser(), "me@x.com").status_code == 401


def test_6_second_change_kills_the_first_link(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    c.post("/api/auth/email", json={"email": "a@x.com"})
    first = token_of(outbox[-1])
    c.post("/api/auth/email", json={"email": "b@x.com"})
    assert browser().post("/api/auth/email/confirm", json={"token": first}).status_code == 422


def test_6_protect_link_locks_the_account_even_after_the_attacker_changes_password(outbox, fast_hash):
    owner = browser()
    signed_up(owner, outbox)
    login(owner)
    attacker = browser()
    attacker.post("/api/auth/login", json={"email": "me@x.com", "password": PW}, headers={"user-agent": "evil"})
    protect = token_of(outbox[-1])  # 주인 메일함의 새 기기 알림
    assert attacker.post("/api/auth/reauth", json={"password": PW}).status_code == 200
    assert attacker.post("/api/auth/password", json={"password": PW2}).status_code == 200  # 탈취자가 변경(버전 오름)
    assert browser().get(f"/api/auth/protect/check?token={protect}").json() == {"valid": True}
    assert browser().post("/api/auth/protect", json={"token": protect}).status_code == 200
    assert attacker.get("/api/auth/me").status_code == 401
    assert login(browser(), pw=PW2).status_code == 401  # 잠김 — 로그인 불가(보호 링크도 로그인 권한 없음)
    assert browser().post("/api/auth/protect", json={"token": protect}).status_code == 422  # 1회


def test_6_email_change_needs_recent_auth(outbox, fast_hash):
    from kumoniji.accounts import db

    c = browser()
    signed_up(c, outbox)
    login(c)
    with db.tx() as cur:
        cur.execute("UPDATE sessions SET reauth_at = now() - interval '10 minutes'")
    assert c.post("/api/auth/email", json={"email": "new@x.com"}).status_code == 403
