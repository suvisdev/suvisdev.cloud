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
        # 다시 받기(REPLAY) 구간이 지난 뒤
        c.execute(f"UPDATE spent_refresh SET spent_at = now() - interval '{sessions.REPLAY + 1} seconds'")
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
        access2, _ = sessions.refresh(c, r1, retry="tabA")  # 탭 A가 먼저 회전
        with pytest.raises(sessions.Raced):
            sessions.refresh(
                c, r1, retry="tabB"
            )  # 탭 B가 같은 옛 토큰으로 바로 뒤에 — 탈취가 아님(키가 달라 다시 주진 않음)
        assert sessions.current(c, access2)  # 아무것도 폐기되지 않음
        c.execute(f"UPDATE spent_refresh SET spent_at = now() - interval '{sessions.RACE_GRACE + 1} seconds'")
        with pytest.raises(sessions.Reused):
            sessions.refresh(c, r1)  # 시간이 지난 뒤의 재사용은 탈취로 봄
    assert sent == ["security"]


def test_11_lost_refresh_response_is_handed_out_again_only_with_the_same_retry_key(database, monkeypatch):
    """응답을 못 받고 끊은 클라이언트가 같은 재시도 키로 다시 오면 같은 새 토큰 — 끊어도 모든 기기 로그아웃이 안 되게.
    키는 클라이언트 메모리에만 있어 훔친 토큰(키 없음·다른 키)엔 열리지 않는다(앱 리뷰 48·49·50차)."""
    monkeypatch.setattr(sessions.mail, "send", lambda *a, **k: None)
    with db.tx() as c:
        _, r1 = sessions.create(c, make_account(email="r1@x.com"), mfa_passed=True)
        _, r2 = sessions.refresh(c, r1, retry="k1")  # 서버는 회전했는데 응답이 사라짐
        c.execute(f"UPDATE spent_refresh SET spent_at = now() - interval '{sessions.REPLAY - 10} seconds'")
        access, again = sessions.refresh(c, r1, retry="k1")
        assert again == r2 and sessions.current(c, access)
        sessions.refresh(c, r2, retry="k2")  # 새 토큰이 쓰였다 — 더는 다시 주지 않는다(같은 키라 탈취로 보진 않음)
        assert sessions.refresh(c, r1, retry="k1") is None
    for thief_key in ["", "guess"]:
        with db.tx() as c:
            _, r1 = sessions.create(c, make_account(email=f"t{thief_key}@x.com"), mfa_passed=True)
            access2, _ = sessions.refresh(c, r1, retry="k1")
            c.execute(f"UPDATE spent_refresh SET spent_at = now() - interval '{sessions.RACE_GRACE + 1} seconds'")
            with pytest.raises(sessions.Reused):  # 키 없이·다른 키로 회전 전 토큰 — 다시 주지 않고 탈취로 봄
                sessions.refresh(c, r1, retry=thief_key)
            assert sessions.current(c, access2) is None
    with db.tx() as c:  # 같은 브라우저의 다른 탭이 이미 두 번 회전 — 같은 키면 사슬을 따라가 지금 토큰을 준다(34차)
        _, r1 = sessions.create(c, make_account(email="r4@x.com"), mfa_passed=True)
        _, r2 = sessions.refresh(c, r1, retry="k1")
        access3, r3 = sessions.refresh(c, r2, retry="k1")
        _, r4 = sessions.refresh(c, r3, retry="k1")  # 이 응답도 잃음
        c.execute("UPDATE spent_refresh SET spent_at = now() - interval '1 minute'")
        assert sessions.refresh(c, r2, retry="k1")[1] == r4  # 늦은 응답이 쿠키를 r2로 되돌렸어도
        assert sessions.current(c, access3)
    with db.tx() as c:  # 사슬 중간을 다른 키가 썼으면(다른 브라우저) 따라가지 않는다
        _, r1 = sessions.create(c, make_account(email="r5@x.com"), mfa_passed=True)
        _, r2 = sessions.refresh(c, r1, retry="k1")
        _, r3 = sessions.refresh(c, r2, retry="k2")
        sessions.refresh(c, r3, retry="k1")
        c.execute("UPDATE spent_refresh SET spent_at = now() - interval '1 minute'")
        assert sessions.refresh(c, r1, retry="k1") is None
    with db.tx() as c:  # 같은 키인데 다시 받기 시간이 지남 — 다른 기기는 그대로(앱 리뷰 57차), 이 세션은 끊는다(66차)
        acct = make_account(email="r3@x.com")
        other, _ = sessions.create(c, acct, mfa_passed=True)
        _, r1 = sessions.create(c, acct, mfa_passed=True)
        thief, r2 = sessions.refresh(c, r1, retry="k1")  # 쿠키와 키를 함께 훔친 사람이 먼저 갱신
        c.execute(f"UPDATE spent_refresh SET spent_at = now() - interval '{sessions.REPLAY + 1} seconds'")
        assert sessions.refresh(c, r1, retry="k1") is None  # 주인이 늦게 돌아옴
        assert sessions.current(c, other)
        assert sessions.current(c, thief) is None and sessions.refresh(c, r2, retry="k1") is None


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


def test_too_many_replays_in_a_day_are_treated_as_theft(database, monkeypatch):
    """웹은 재시도 키가 리프레시와 같은 쿠키 통에 있어 둘을 함께 훔치면 다시 받기로 탐지 없이 이어 받는다.
    정상 다시 받기(응답 유실)는 드무니 하루 MAX_REPLAYS를 넘으면 전 세션 폐기·보안 메일(앱 리뷰 40차)."""
    sent = []
    monkeypatch.setattr(sessions.mail, "send", lambda to, kind, path, lang="en": sent.append(kind))
    with db.tx() as c:
        acct = make_account(email="rp@x.com")
        other, _ = sessions.create(c, acct, mfa_passed=True)
        _, r1 = sessions.create(c, acct, mfa_passed=True)
        _, r2 = sessions.refresh(c, r1, retry="k1")
        for _ in range(sessions.MAX_REPLAYS * 2):  # 방금 회전 — 같은 브라우저 탭들의 동시 갱신이라 따로 셈(41·46차)
            assert sessions.refresh(c, r1, retry="k1")[1] == r2
        # 훔친 사람은 주인이 회전할 때마다 그 토큰을 다시 받는다 — 회전마다 하나씩 센다(같은 토큰은 한 번만, 56차)
        cur = r2
        for i in range(sessions.MAX_REPLAYS + 1):
            _, new = sessions.refresh(c, cur, retry="k1")
            c.execute(f"UPDATE spent_refresh SET spent_at = now() - interval '{sessions.RACE_GRACE + 1} seconds'")
            if i == sessions.MAX_REPLAYS:
                with pytest.raises(sessions.Reused):
                    sessions.refresh(c, cur, retry="k1")
            else:
                assert sessions.refresh(c, cur, retry="k1")[1] == new  # 여기까진 정상 범위
            cur = new
        assert sessions.current(c, other) is None
    assert sent == ["security"]
    with db.tx() as c:  # 하루가 지나면 다시 1부터
        _, r1 = sessions.create(c, make_account(email="rq@x.com"), mfa_passed=True)
        _, r2 = sessions.refresh(c, r1, retry="k1")
        c.execute(f"UPDATE spent_refresh SET spent_at = now() - interval '{sessions.RACE_GRACE + 1} seconds'")
        for _ in range(sessions.MAX_REPLAYS):
            sessions.refresh(c, r1, retry="k1")
        c.execute("UPDATE sessions SET replayed_at = now() - interval '25 hours' WHERE replays > 0")  # 다른 날
        assert sessions.refresh(c, r1, retry="k1")[1] == r2


def test_replay_race_grace_is_judged_by_the_first_token(database, monkeypatch):
    """사슬을 따라갈 때 정상 경합인지는 처음 보낸 토큰으로 본다 — 사슬 끝이 방금 회전됐어도 처음 토큰이 오래됐으면
    센다(앱 리뷰 44차). 안 그러면 훔친 두 쿠키로 회전을 계속 새로 만들며 한도를 피한다."""
    monkeypatch.setattr(sessions.mail, "send", lambda *a, **k: None)
    with db.tx() as c:
        _, r1 = sessions.create(c, make_account(email="rg@x.com"), mfa_passed=True)
        cur = r1
        for i in range(sessions.MAX_REPLAYS + 1):
            _, a = sessions.refresh(c, cur, retry="k1")
            c.execute(
                f"UPDATE spent_refresh SET spent_at = now() - interval '{sessions.RACE_GRACE + 1} seconds'"
            )
            _, b = sessions.refresh(c, a, retry="k1")  # 사슬 끝(a)은 방금 회전
            if i == sessions.MAX_REPLAYS:
                with pytest.raises(sessions.Reused):
                    sessions.refresh(c, cur, retry="k1")
            else:
                assert sessions.refresh(c, cur, retry="k1")[1] == b
            cur = b


def test_replay_locks_the_account_before_the_session(database):
    """다시 받기는 계정 행을 먼저 잠근다 — 비밀번호 변경(계정 → 세션 순)과 잠금 순서를 맞춰 교착을 막는다(앱 리뷰 45차)."""
    import psycopg

    with db.tx() as c:
        acct = make_account(email="lk@x.com")
        _, r1 = sessions.create(c, acct, mfa_passed=True)
        sessions.refresh(c, r1, retry="k1")
    with db.tx() as c:
        sessions.refresh(c, r1, retry="k1")  # 다시 받기 — 이 트랜잭션이 끝날 때까지 계정 행을 쥔다
        with db.tx() as other:
            with pytest.raises(psycopg.errors.LockNotAvailable):
                other.execute("SELECT 1 FROM accounts WHERE id = %s FOR UPDATE NOWAIT", (acct,))


def test_concurrent_refresh_races_have_their_own_daily_cap(database, monkeypatch):
    """방금 회전된 토큰의 다시 받기는 정상 경합이라 MAX_REPLAYS에 넣지 않지만, 끝없이 봐주지는 않는다(앱 리뷰 46차)."""
    sent = []
    monkeypatch.setattr(sessions.mail, "send", lambda to, kind, path, lang="en": sent.append(kind))
    with db.tx() as c:
        acct = make_account(email="rc@x.com")
        _, r1 = sessions.create(c, acct, mfa_passed=True)
        # 탭 4개가 회전마다 함께 갱신해도 회전당 한 번만 센다(57차) — 하루 정상 회전 수(액세스 15분 → 96)로는 안 걸리고,
        # 회전을 계속 새로 만들며 따라붙어야 한도에 닿는다
        cur = r1
        for i in range(sessions.MAX_RACES + 1):
            _, new = sessions.refresh(c, cur, retry="k1")
            if i == sessions.MAX_RACES:
                with pytest.raises(sessions.Reused):
                    sessions.refresh(c, cur, retry="k1")
                break
            for _ in range(3):
                assert sessions.refresh(c, cur, retry="k1")[1] == new
            if i == 0:
                assert c.execute("SELECT races FROM sessions WHERE revoked_at IS NULL").fetchone()["races"] == 1
            cur = new
    assert sent == ["security"]


def test_revoke_all_locks_the_account_before_sessions(database):
    """전 세션 폐기도 계정 행부터 잠근다 — 다시 받기(계정 → 세션)와 순서가 엇갈리면 교착한다(앱 리뷰 47차)."""
    import threading

    import psycopg

    with db.tx() as c:
        acct = make_account(email="ra@x.com")
        sessions.create(c, acct, mfa_passed=True)
    done = threading.Event()
    with db.tx() as holder:
        holder.execute("SELECT 1 FROM sessions WHERE account_id = %s FOR UPDATE", (acct,))  # 다른 요청이 세션 행을 쥠

        def logout_everywhere():
            with db.tx() as c:
                c.execute("SET LOCAL lock_timeout = '3s'")
                sessions.revoke_all(c, acct)
            done.set()

        t = threading.Thread(target=logout_everywhere)
        t.start()
        time.sleep(0.5)
        with db.tx() as probe:  # 세션을 기다리는 동안 계정 행은 이미 쥐고 있어야 한다
            with pytest.raises(psycopg.errors.LockNotAvailable):
                probe.execute("SELECT 1 FROM accounts WHERE id = %s FOR UPDATE NOWAIT", (acct,))
    t.join(5)
    assert done.is_set()


def test_a_fresh_replay_from_another_ip_counts_as_a_replay(database, monkeypatch):
    """방금 회전된 토큰의 다시 받기라도 회전한 요청과 IP가 다르면 동시 갱신이 아니라 다시 받기로 센다 — 쿠키를 함께
    훔친 사람이 회전마다 30초 안에 따라붙어 경합 한도(하루 192)로 버티지 못하게(앱 리뷰 52차)."""
    monkeypatch.setattr(sessions.mail, "send", lambda *a, **k: None)
    with db.tx() as c:
        _, r1 = sessions.create(c, make_account(email="ip@x.com"), mfa_passed=True)
        cur = r1
        for i in range(sessions.MAX_REPLAYS + 1):
            _, new = sessions.refresh(c, cur, retry="k1", ip="1.1.1.1")  # 주인이 회전
            if i == sessions.MAX_REPLAYS:
                with pytest.raises(sessions.Reused):
                    sessions.refresh(c, cur, retry="k1", ip="2.2.2.2")
            else:
                assert sessions.refresh(c, cur, retry="k1", ip="2.2.2.2")[1] == new  # 훔친 쪽이 바로 따라붙음
            cur = new


def test_many_tabs_replaying_one_lost_response_count_once(database, monkeypatch):
    """응답 하나를 잃고 30초 뒤 같은 쿠키의 탭 여럿이 다시 받아도 한 번만 센다 — 한도를 넘어 모든 세션을 끊지 않게
    (앱 리뷰 56차). 다른 토큰(회전마다)의 다시 받기는 여전히 하나씩 센다."""
    monkeypatch.setattr(sessions.mail, "send", lambda *a, **k: None)
    with db.tx() as c:
        _, r1 = sessions.create(c, make_account(email="tabs@x.com"), mfa_passed=True)
        _, r2 = sessions.refresh(c, r1, retry="k1", ip="1.1.1.1")  # 응답을 잃은 회전
        c.execute("UPDATE spent_refresh SET spent_at = now() - interval '1 minute'")
        for _ in range(sessions.MAX_REPLAYS + 3):
            assert sessions.refresh(c, r1, retry="k1", ip="1.1.1.1")[1] == r2
        assert c.execute("SELECT replays FROM sessions").fetchone()["replays"] == 1


def test_a_tab_race_does_not_hide_a_replay_from_another_ip(database, monkeypatch):
    """같은 브라우저 탭들의 동시 갱신이 토큰을 먼저 '셌다'고 표시해도 다른 IP의 다시 받기는 따로 센다(앱 리뷰 58차)."""
    monkeypatch.setattr(sessions.mail, "send", lambda *a, **k: None)
    with db.tx() as c:
        _, cur = sessions.create(c, make_account(email="mix@x.com"), mfa_passed=True)
        for i in range(sessions.MAX_REPLAYS + 1):
            _, new = sessions.refresh(c, cur, retry="k1", ip="1.1.1.1")
            assert sessions.refresh(c, cur, retry="k1", ip="1.1.1.1")[1] == new  # 탭의 동시 갱신
            if i == sessions.MAX_REPLAYS:
                with pytest.raises(sessions.Reused):
                    sessions.refresh(c, cur, retry="k1", ip="2.2.2.2")
            else:
                assert sessions.refresh(c, cur, retry="k1", ip="2.2.2.2")[1] == new  # 훔친 쪽
            cur = new


def test_a_web_tab_race_on_a_revoked_session_ends_the_session_instead_of_409(database):
    a = make_account()
    with db.tx() as c:
        access, r1 = sessions.create(c, a, mfa_passed=True)
        key = sessions.retry_key(sessions.decode(access)["sid"])
        sessions.refresh(c, r1, retry=key, ip="1.1.1.1")  # 이 탭이 회전했지만 응답을 잃음
        sessions.revoke_all(c, a)  # 그사이 비밀번호 재설정 등으로 폐기
        assert sessions.refresh(c, r1, retry=key, ip="1.1.1.1") is None  # 409(Raced)가 아니라 끝


def test_same_client_that_cannot_be_reissued_ends_its_session_even_soon_after(database):
    a = make_account()
    with db.tx() as c:
        access, r1 = sessions.create(c, a, mfa_passed=True)
        key = sessions.retry_key(sessions.decode(access)["sid"])
        tok = r1
        for _ in range(sessions.CHAIN + 2):  # 쿠키와 키를 함께 가진 쪽이 추적 한도를 넘겨 앞서감
            _, tok = sessions.refresh(c, tok, retry=key, ip="9.9.9.9")
        c.execute(f"UPDATE spent_refresh SET spent_at = now() - interval '{sessions.RACE_GRACE + 1} seconds'")
        assert sessions.refresh(c, r1, retry=key, ip="1.1.1.1") is None  # 주인은 쫓겨나지만
        assert sessions.refresh(c, tok, retry=key, ip="9.9.9.9") is None  # 앞서간 쪽의 최신 토큰도 끊긴다


def test_a_web_cookie_pair_from_another_ip_right_after_rotation_gets_409_not_tokens(database):
    a = make_account()
    with db.tx() as c:
        access, r1 = sessions.create(c, a, mfa_passed=True)
        key = sessions.retry_key(sessions.decode(access)["sid"])
        sessions.refresh(c, r1, retry=key, ip="1.1.1.1")  # 주인이 회전
        with pytest.raises(sessions.Raced):
            sessions.refresh(c, r1, retry=key, ip="6.6.6.6")  # 훔친 옛 쿠키 쌍, 다른 IP
