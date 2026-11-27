"""검증 8: 탈퇴 — 재인증, 즉시 차단, 개인정보 파기, 복원 뒤 재삭제, 재가입."""

import time

from kumoniji.accounts import db, service

from .helpers import PW, browser, id_token, login, run_flow, signed_up


def test_8_delete_blocks_access_and_wipes_personal_data(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    assert c.post("/api/games", json={"rid": "beforedelete"}).status_code == 200  # 하트·원장
    assert c.post("/api/wallet/attend").status_code == 200  # 출석·일일 기록
    with db.tx() as cur:
        cur.execute("UPDATE sessions SET reauth_at = now() - interval '10 minutes'")
    assert c.post("/api/auth/delete").status_code == 403  # 최근 인증 필요
    c.post("/api/auth/reauth", json={"password": PW})
    assert c.post("/api/auth/delete").status_code == 200
    assert c.get("/api/auth/me").status_code == 401
    assert login(browser()).status_code == 401
    with db.tx() as cur:
        a = cur.execute(
            "SELECT email, nickname, pw_hash, verified_at, mfa_last_step, locked_at FROM accounts"
        ).fetchone()
        # 인증·2단계 마지막 시각·잠금 시각도 — 방침은 가입·탈퇴 시각만 남는다고 안내(약관 리뷰 4차)
        assert a == {
            "email": None,
            "nickname": "",
            "pw_hash": None,
            "verified_at": None,
            "mfa_last_step": None,
            "locked_at": None,
        }
        for table in ("wallets", "ledger", "daily"):  # 화폐 기록도 함께 파기(리뷰 지적)
            assert cur.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"] == 0, table
    signed_up(browser(), outbox)  # 같은 주소로 새로 가입 가능(옛 계정 부활 아님)
    with db.tx() as cur:
        assert cur.execute("SELECT count(*) AS n FROM accounts WHERE deleted_at IS NULL").fetchone()["n"] == 1


def test_8_restored_backup_is_purged_again(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    c.post("/api/auth/reauth", json={"password": PW})
    c.post("/api/auth/delete")
    with db.tx() as cur:  # 탈퇴 전 백업을 복원한 상황을 흉내(삭제 이력만 남음)
        cur.execute(
            "UPDATE accounts SET email = 'me@x.com', email_key = 'me@x.com', nickname = 'me', deleted_at = NULL"
        )
        assert service.purge_deleted(cur) == 1
        cur.execute("UPDATE accounts SET mfa_last_step = 123")  # 시각 칸만 되살아나도 다시 지운다
        assert service.purge_deleted(cur) == 1
        assert cur.execute("SELECT mfa_last_step FROM accounts").fetchone()["mfa_last_step"] is None
        assert service.purge_deleted(cur) == 0
    assert login(browser()).status_code == 401


def test_8_google_only_account_reauths_with_google_then_deletes(outbox, google_keys, monkeypatch):
    g = browser()
    run_flow(g, monkeypatch)
    with db.tx() as cur:
        cur.execute("UPDATE sessions SET reauth_at = now() - interval '10 minutes'")
    assert g.post("/api/auth/delete").status_code == 403

    def stale(n):
        return id_token(n, auth_time=int(time.time()) - 3600)

    def fresh(n):
        return id_token(n, auth_time=int(time.time()))

    run_flow(g, monkeypatch, token_for=stale, path="/api/auth/google/start?reauth=true")
    assert g.post("/api/auth/delete").status_code == 403  # 구글에서 오래전 로그인 → 인정 안 함
    r = run_flow(g, monkeypatch, token_for=fresh, path="/api/auth/google/start?reauth=true")
    assert r.headers["location"] == "/?reauthed=google"
    assert g.post("/api/auth/delete").status_code == 200


def test_8_deleted_account_row_is_not_swept_as_an_unverified_signup(outbox, fast_hash):
    """탈퇴 기록(계정 번호·가입 시각)은 남는다 — 탈퇴로 verified_at이 비어도 미인증 가입 정리에 걸리지 않게(약관 리뷰 5차)"""
    c = browser()
    signed_up(c, outbox)
    login(c)
    c.post("/api/auth/reauth", json={"password": PW})
    assert c.post("/api/auth/delete").status_code == 200
    with db.tx() as cur:
        cur.execute("UPDATE accounts SET created_at = now() - interval '2 days'")
        assert service.purge_unverified(cur) == 0
        assert cur.execute("SELECT count(*) AS n FROM accounts").fetchone()["n"] == 1


def test_8_mfa_setup_racing_a_deletion_does_not_store_a_secret(outbox, fast_hash, monkeypatch):
    """세션 확인 뒤 탈퇴가 먼저 커밋되면 2단계 비밀값을 지운 계정에 쓰지 않는다(약관 리뷰 9차)"""
    from kumoniji.accounts import mfa

    c = browser()
    signed_up(c, outbox)
    login(c)
    real = mfa.require_recent

    def deleted_meanwhile(s):
        real(s)
        with db.tx() as cur:
            cur.execute("UPDATE accounts SET deleted_at = now()")

    monkeypatch.setattr(mfa, "require_recent", deleted_meanwhile)
    assert c.post("/api/auth/mfa/setup").status_code == 401
    with db.tx() as cur:
        assert cur.execute("SELECT mfa_secret FROM accounts").fetchone()["mfa_secret"] is None


def test_8_repurge_keeps_the_first_purge_time(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    c.post("/api/auth/reauth", json={"password": PW})
    c.post("/api/auth/delete")
    with db.tx() as cur:
        first = cur.execute("SELECT purged_at FROM deletion_log").fetchone()["purged_at"]
        cur.execute("UPDATE accounts SET mfa_secret = 'x'")  # 남은 칸이 생겨 다시 정리
        assert service.purge_deleted(cur) == 1
        assert cur.execute("SELECT purged_at FROM deletion_log").fetchone()["purged_at"] == first


def test_8_leftovers_written_by_a_racing_request_are_swept(outbox, fast_hash):
    """탈퇴와 겹친 요청이 탈퇴 뒤에 남긴 주소 변경 링크·복구 코드도 다음 정리가 거둔다(약관 리뷰 10차)"""
    c = browser()
    signed_up(c, outbox)
    login(c)
    c.post("/api/auth/reauth", json={"password": PW})
    c.post("/api/auth/delete")
    with db.tx() as cur:
        aid = cur.execute("SELECT id FROM accounts").fetchone()["id"]
        from kumoniji.accounts import tokens

        tokens.issue(cur, aid, "email", service.EMAIL_TTL, target="new@x.com")
        assert service.purge_deleted(cur) == 1
        assert cur.execute("SELECT count(*) AS n FROM auth_tokens").fetchone()["n"] == 0
