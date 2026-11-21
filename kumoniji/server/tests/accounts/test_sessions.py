"""검증 11·12: 토큰 검증·회전, 세션 영속성."""

import time

import jwt
import pytest

from kumoniji.accounts import db, sessions

from .helpers import make_account

KEY = "k" * 48


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setenv("KUMONIJI_JWT_SECRET", KEY)


def test_11_refresh_rotates_and_reuse_revokes_everything(database, monkeypatch):
    sent = []
    monkeypatch.setattr(sessions.mail, "send", lambda to, kind, path, lang="en": sent.append(kind))
    a = make_account()
    with db.tx() as c:
        access, r1 = sessions.create(c, a, mfa_passed=True)
        other_access, _ = sessions.create(c, a, mfa_passed=True)  # 다른 기기
        access2, r2 = sessions.refresh(c, r1)
        assert r2 != r1 and sessions.current(c, access2)
        c.execute("UPDATE spent_refresh SET spent_at = now() - interval '1 minute'")  # 동시 갱신 유예가 지난 뒤
        with pytest.raises(sessions.Reused):
            sessions.refresh(c, r1)  # 이미 회전된 토큰 재사용 → 탈취로 봄
        assert sessions.current(c, access2) is None
        assert sessions.current(c, other_access) is None  # 모든 기기
        assert sessions.refresh(c, r2) is None
    assert sent == ["security"]


def test_11_stolen_token_reused_after_the_owner_refreshed_twice_still_revokes(database, monkeypatch):
    sent = []
    monkeypatch.setattr(sessions.mail, "send", lambda to, kind, path, lang="en": sent.append(kind))
    a = make_account()
    with db.tx() as c:
        _, stolen = sessions.create(c, a, mfa_passed=True)
        _, r2 = sessions.refresh(c, stolen)  # 주인이 계속 쓴다
        access3, _ = sessions.refresh(c, r2)
        c.execute("UPDATE spent_refresh SET spent_at = now() - interval '1 minute'")
        with pytest.raises(sessions.Reused):
            sessions.refresh(c, stolen)  # 두 번 전 토큰도 탈취로 봄
        assert sessions.current(c, access3) is None
    assert sent == ["security"]


def test_11_spent_tokens_are_forgotten_after_30_days(database):
    a = make_account()
    with db.tx() as c:
        _, r1 = sessions.create(c, a, mfa_passed=True)
        sessions.refresh(c, r1)
        c.execute("UPDATE spent_refresh SET spent_at = now() - interval '31 days'")
        sessions.sweep(c)
        assert c.execute("SELECT count(*) AS n FROM spent_refresh").fetchone()["n"] == 0


def test_11_two_tabs_refreshing_at_once_do_not_log_everyone_out(database, monkeypatch):
    sent = []
    monkeypatch.setattr(sessions.mail, "send", lambda to, kind, path, lang="en": sent.append(kind))
    a = make_account()
    with db.tx() as c:
        _, r1 = sessions.create(c, a, mfa_passed=True)
        access2, _ = sessions.refresh(c, r1)  # 탭 A가 먼저 회전
        with pytest.raises(sessions.Raced):
            sessions.refresh(c, r1)  # 탭 B가 같은 옛 토큰으로 바로 뒤에 — 탈취가 아님
        assert sessions.current(c, access2)  # 아무것도 폐기되지 않음
        c.execute(f"UPDATE spent_refresh SET spent_at = now() - interval '{sessions.RACE_GRACE + 1} seconds'")
        with pytest.raises(sessions.Reused):
            sessions.refresh(c, r1)  # 시간이 지난 뒤의 재사용은 탈취로 봄
    assert sent == ["security"]


def test_11_idle_30_days_and_no_absolute_expiry(database):
    a = make_account()
    with db.tx() as c:
        _, r = sessions.create(c, a, mfa_passed=True)
        c.execute(
            "UPDATE sessions SET created_at = now() - interval '400 days', last_used_at = now() - interval '29 days'"
        )
        _, r = sessions.refresh(c, r)  # 1년 넘은 세션도 계속 쓰면 유지
        c.execute("UPDATE sessions SET last_used_at = now() - interval '31 days'")
        assert sessions.refresh(c, r) is None  # 30일 안 쓰면 만료


def _forge(**over):
    now = int(time.time())
    claims = {"sub": "1", "sid": "x", "ver": 1, "typ": "access", "iss": "kumoniji", "aud": "kumoniji", "exp": now + 60}
    claims.update(over)
    return claims


def test_11_rejects_tampered_tokens(database):
    a = make_account()
    with db.tx() as c:
        good, refresh_raw = sessions.create(c, a, mfa_passed=True)
        sid = jwt.decode(good, options={"verify_signature": False})["sid"]
        base = _forge(sub=str(a), sid=sid)
        assert sessions.current(c, jwt.encode(base, KEY, "HS256"))
        bad = [
            jwt.encode(base, "other" * 10, "HS256"),
            jwt.encode(base, None, "none"),
            jwt.encode(base | {"exp": int(time.time()) - 5}, KEY, "HS256"),
            jwt.encode(base | {"iss": "evil"}, KEY, "HS256"),
            jwt.encode(base | {"aud": "evil"}, KEY, "HS256"),
            jwt.encode(base | {"typ": "refresh"}, KEY, "HS256"),
            refresh_raw,  # 리프레시를 액세스로
        ]
        assert all(sessions.current(c, t) is None for t in bad)


def test_12_logout_and_revoke_all_are_immediate(database):
    a = make_account()
    with db.tx() as c:
        t1, _ = sessions.create(c, a, mfa_passed=True)
        t2, _ = sessions.create(c, a, mfa_passed=True)
        sid1 = sessions.current(c, t1)["sid"]
        sessions.revoke(c, a, sid1)
        assert sessions.current(c, t1) is None and sessions.current(c, t2)
        sessions.revoke_all(c, a)
        assert sessions.current(c, t2) is None


def test_12_refresh_does_not_extend_recent_auth(database):
    a = make_account()
    with db.tx() as c:
        _, r = sessions.create(c, a, mfa_passed=True)
        c.execute("UPDATE sessions SET reauth_at = now() - interval '10 minutes'")
        access, _ = sessions.refresh(c, r)
        assert sessions.current(c, access)["reauth_age"] > 590
