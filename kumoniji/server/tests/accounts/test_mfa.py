"""검증 7·8: 2단계 인증 — 켜기·로그인 관문·재사용 차단·복구 코드·끄기."""

import pyotp
import pytest
from cryptography.fernet import Fernet

from .helpers import PW, browser, login, signed_up


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setenv("KUMONIJI_TOTP_KEY", Fernet.generate_key().decode())


def turned_on(outbox):
    c = browser()
    signed_up(c, outbox)
    login(c)
    secret = c.post("/api/auth/mfa/setup").json()["secret"]
    assert c.get("/api/auth/me").json()["mfa_enabled"] is False  # 맞히기 전엔 꺼져 있음
    r = c.post("/api/auth/mfa/enable", json={"code": pyotp.TOTP(secret).now()})
    assert r.status_code == 200
    return c, secret, r.json()["recovery_codes"]


def test_7_login_requires_mfa_before_playing(outbox, fast_hash):
    _, secret, _ = turned_on(outbox)
    d = browser()
    assert login(d).json()["mfa_required"] is True
    assert d.post("/api/games").status_code == 403  # MFA 전 세션은 게임 불가
    assert d.post("/api/auth/mfa/verify", json={"code": "000000"}).status_code == 401
    # 켤 때 쓴 코드와 같은 칸이면 재사용으로 거부될 수 있으니 다음 칸 코드를 쓴다
    import time

    code = pyotp.TOTP(secret).at(int(time.time()) + 30)
    assert d.post("/api/auth/mfa/verify", json={"code": code}).status_code == 200
    assert d.post("/api/games").status_code == 200


def test_7_same_code_cannot_be_used_twice(outbox, fast_hash):
    _, secret, _ = turned_on(outbox)
    import time

    code = pyotp.TOTP(secret).at(int(time.time()) + 30)
    a, b = browser(), browser()
    login(a)
    login(b)
    assert a.post("/api/auth/mfa/verify", json={"code": code}).status_code == 200
    assert b.post("/api/auth/mfa/verify", json={"code": code}).status_code == 401


def test_8_recovery_code_works_once(outbox, fast_hash):
    _, _, codes = turned_on(outbox)
    assert len(codes) == 10 and len(set(codes)) == 10
    a, b = browser(), browser()
    login(a)
    login(b)
    assert a.post("/api/auth/mfa/verify", json={"code": codes[0].upper()}).status_code == 200
    assert b.post("/api/auth/mfa/verify", json={"code": codes[0]}).status_code == 401


def test_7_enable_logs_out_other_devices_and_mails(outbox, fast_hash):
    other = browser()
    signed_up(other, outbox)
    login(other)
    c = browser()
    login(c)
    secret = c.post("/api/auth/mfa/setup").json()["secret"]
    c.post("/api/auth/mfa/enable", json={"code": pyotp.TOTP(secret).now()})
    assert other.get("/api/auth/me").status_code == 401
    assert c.post("/api/games").status_code == 200
    assert outbox[-1]["kind"] == "security"


def test_7_mfa_changes_need_recent_auth(outbox, fast_hash):
    c, secret, codes = turned_on(outbox)
    from kumoniji.accounts import db

    with db.tx() as cur:
        cur.execute("UPDATE sessions SET reauth_at = now() - interval '10 minutes'")
    assert c.post("/api/auth/mfa/disable", json={"code": codes[1]}).status_code == 403
    assert c.post("/api/auth/mfa/recovery").status_code == 403
    assert c.post("/api/auth/reauth", json={"password": PW}).status_code == 200
    assert c.post("/api/auth/mfa/disable", json={"code": codes[1]}).status_code == 200
    d = browser()
    assert login(d).json()["mfa_required"] is False


def test_7_wrong_codes_slow_down(outbox, fast_hash):
    turned_on(outbox)
    d = browser()
    login(d)
    codes = [d.post("/api/auth/mfa/verify", json={"code": "000000"}).status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]
