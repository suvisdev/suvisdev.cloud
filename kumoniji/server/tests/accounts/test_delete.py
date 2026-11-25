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
        a = cur.execute("SELECT email, nickname, pw_hash FROM accounts").fetchone()
        assert a == {"email": None, "nickname": "", "pw_hash": None}
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
