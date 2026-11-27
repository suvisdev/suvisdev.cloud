import time
from contextlib import contextmanager

import pytest

from kumoniji import api
from kumoniji.accounts import db
from kumoniji.wallet import money, store, web

from .helpers import browser, login, make_account, signed_up

S0 = {"five": 0, "triple": 0, "oddeven": 0, "fullhouse": 0, "today": 0}


def P(a, rank, points, left=3, stats=S0):
    return {"account": a, "stats": stats, "rank": rank, "left": left, "points": points}


def test_new_wallet_has_ten_hearts_and_nothing_else(database):
    a = make_account()
    with db.tx() as c:
        w = store.snapshot(c, a, time.time())
    assert (w["coins"], w["gems"], w["hearts"], w["next_heart"]) == (0, 0, 10, None)


def test_heart_used_from_full_refills_ten_minutes_later(database):
    a = make_account()
    t = float(int(time.time()) + 2)  # 정수(timestamptz 반올림 회피), 지갑을 만든 시각보다 뒤
    with db.tx() as c:
        assert store.use_heart(c, a, t)
        assert store.snapshot(c, a, t)["hearts"] == 9
        assert store.snapshot(c, a, t + money.HEART_EVERY)["hearts"] == 10
        ledger = c.execute("SELECT coalesce(sum(hearts), 0) AS s FROM ledger WHERE account_id = %s", (a,)).fetchone()
    assert 10 + ledger["s"] == 10  # 처음 10 + 원장(쓴 -1, 충전 +1) = 잔고


def test_auto_match_game_moves_coins_once_even_if_recorded_twice(database):
    ids = [make_account(email=f"w{i}@x.com", nickname=f"w{i}") for i in range(4)]
    with db.tx() as c:
        for a in ids:
            c.execute("INSERT INTO wallets (account_id, coins) VALUES (%s, 10000)", (a,))
    players = [P(ids[0], 1, 60, left=0), P(ids[1], 2, -10), P(ids[2], 3, -20), P(ids[3], 4, -30)]
    for _ in range(2):  # 같은 판을 두 번 기록해도(재시도) 한 번만
        with db.tx() as c:
            store.finish_game(c, "t1", players, time.time(), stake=True)
    with db.tx() as c:
        got = [store.snapshot(c, a, time.time()) for a in ids]
    # 0번은 판돈 +3,000에 low3·score30 미션 보상, 나머지는 low3(손패 3장) 보상만
    assert [w["coins"] for w in got] == [13000 + 2 * money.MISSION] + [x + money.MISSION for x in (9500, 9000, 8500)]
    assert [w["hearts"] for w in got] == [10, 10, 10, 10]  # 하트는 판 끝이 아니라 들어갈 때 쓴다
    assert got[0]["missions"]["counts"]["games"] == 1


def test_friend_room_and_single_give_points_for_missions_but_no_coins(database):
    a = make_account()
    with db.tx() as c:
        store.finish_game(c, "s1", [P(a, 1, 40, left=0), P(None, 2, -40), P(None, 3, 0), P(None, 4, 0)], time.time(), stake=False)
        w = store.snapshot(c, a, time.time())
    assert w["coins"] == money.MISSION * 2  # low3, score30 달성 → 미션 보상만
    assert set(w["missions"]["done"]) == {"low3", "score30"} and w["hearts"] == 10


def test_five_missions_pay_bonus_once(database):
    a = make_account()
    st = S0 | {"five": 3, "triple": 2, "today": 1, "oddeven": 1, "fullhouse": 1}
    with db.tx() as c:
        for ref in ("g1", "g2"):
            store.finish_game(c, ref, [P(a, 1, 31, left=0, stats=st), P(None, 2, 0), P(None, 3, 0), P(None, 4, 0)], time.time(), stake=False)
        w = store.snapshot(c, a, time.time())
    assert w["missions"]["bonus"] is True and len(w["missions"]["done"]) == 8  # 2판이라 games5만 빠짐
    assert w["coins"] == money.MISSION * 8 + money.MISSION_BONUS


def test_attend_once_a_day_and_seventh_day_gives_more(database):
    a = make_account()
    day = 86400
    t0 = 1764514800  # 2025-12-01 00:00 KST
    with db.tx() as c:
        for i in range(6):
            store.attend(c, a, t0 + i * day)
        assert store.snapshot(c, a, t0 + 6 * day)["attend"]["next"] == 7  # 지금 출석하면 7일째(앱 버튼이 보상을 다르게 안내)
        store.attend(c, a, t0 + 6 * day)
        with pytest.raises(LookupError):
            store.attend(c, a, t0 + 6 * day + 60)
        w = store.snapshot(c, a, t0 + 6 * day + 60)
        assert {k: w["attend"][k] for k in ("day", "streak", "claimed")} == {"day": "2025-12-07", "streak": 7, "claimed": True}
        assert w["coins"] == money.ATTEND * 6 + money.ATTEND_7TH and w["gems"] == money.ATTEND_7TH_GEMS
        with pytest.raises(LookupError):
            store.attend(c, a, t0 + 6 * day - 1)  # 자정 전 요청이 늦게 도착 — 날짜를 되돌리지 않는다
        store.attend(c, a, t0 + 9 * day)  # 하루 걸렀다 → 1일째부터
        assert store.snapshot(c, a, t0 + 9 * day)["attend"]["streak"] == 1
        assert store.snapshot(c, a, t0 + 11 * day)["attend"]["next"] == 1  # 또 걸렀다 → 1일째부터


def test_buy_with_gems_and_hearts_can_exceed_ten(database):
    a = make_account()
    with db.tx() as c:
        c.execute("INSERT INTO wallets (account_id, gems) VALUES (%s, 15)", (a,))
        store.buy(c, a, "hearts5", time.time())
        with pytest.raises(LookupError):
            store.buy(c, a, "hearts5", time.time())  # 보석 5 남음
        w = store.snapshot(c, a, time.time())
    assert (w["gems"], w["hearts"]) == (5, 15)


def test_bigger_packs_give_a_bonus_and_the_api_sells_every_shop_item(database):
    """골드·햇살 묶음은 많이 살수록 덤 — 조각 하나당 받는 양이 줄지 않는다(11-27 상점)."""
    coins = sorted((p, g["coins"]) for p, g in money.SHOP.values() if "coins" in g)
    hearts = sorted((p, g["hearts"]) for p, g in money.SHOP.values() if "hearts" in g)
    for packs in (coins, hearts):
        rates = [n / p for p, n in packs]
        assert rates == sorted(rates) and rates[-1] > rates[0]
    a = make_account()
    with db.tx() as c:
        c.execute("INSERT INTO wallets (account_id, gems) VALUES (%s, 325)", (a,))
        store.buy(c, a, "coins40000", time.time())
        store.buy(c, a, "hearts15", time.time())
        w = store.snapshot(c, a, time.time())
    assert (w["gems"], w["coins"] >= 40000, w["hearts"]) == (0, True, 25)
    assert set(web.Buy.model_fields["item"].annotation.__args__) == set(money.SHOP)


def test_resent_buy_with_the_same_request_id_buys_once(database):
    """구매가 커밋된 뒤 응답이 유실돼 같은 rid로 다시 보내도 보석은 한 번만(Codex 25차)."""
    a = make_account()
    with db.tx() as c:
        c.execute("INSERT INTO wallets (account_id, gems) VALUES (%s, 20)", (a,))
        store.buy(c, a, "hearts5", time.time(), "req-00001")
        w = store.buy(c, a, "hearts5", time.time(), "req-00001")
    assert (w["gems"], w["hearts"]) == (10, 15)


def test_single_game_uses_a_heart_refuses_at_zero_and_records_once(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    v = c.post("/api/games").json()
    assert c.get("/api/wallet").json()["hearts"] == 9
    while v["winner"] is None:
        v = c.post(f"/api/games/{v['id']}/moves", json={"tiles": v["moves"][0] if v["moves"] else []}).json()
    assert v["wallet"]["missions"]["counts"]["games"] == 1
    again = c.get(f"/api/games/{v['id']}").json()  # 다시 읽어도 지갑은 주되 기록은 한 번만
    assert again["wallet"]["missions"]["counts"]["games"] == 1
    with db.tx() as x:
        x.execute("UPDATE wallets SET hearts = 0, hearts_at = now()")
    r = c.post("/api/games")
    assert r.status_code == 402 and r.json()["detail"]["code"] == "no_heart"


def test_resent_new_game_with_same_rid_returns_that_game_without_a_second_heart(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    first = c.post("/api/games", json={"rid": "abcdefgh1"}).json()
    again = c.post("/api/games", json={"rid": "abcdefgh1"}).json()  # 응답을 못 받아 다시 보냄
    assert again["id"] == first["id"] and c.get("/api/wallet").json()["hearts"] == 9
    other = c.post("/api/games", json={"rid": "abcdefgh2"}).json()
    assert other["id"] != first["id"] and c.get("/api/wallet").json()["hearts"] == 8
    with db.tx() as x:
        x.execute("UPDATE wallets SET hearts = 0, hearts_at = now()")
    assert c.post("/api/games", json={"rid": "abcdefgh3"}).status_code == 402
    with db.tx() as x:
        x.execute("UPDATE wallets SET hearts = 1, hearts_at = now()")
    assert c.post("/api/games", json={"rid": "abcdefgh3"}).status_code == 200  # 거절된 rid는 남지 않는다
    api.GAMES.pop(first["id"])  # 판이 메모리에서 밀려난 뒤 같은 rid가 다시 와도 하트를 다시 쓰지 않는다
    before = c.get("/api/wallet").json()["hearts"]
    assert c.post("/api/games", json={"rid": "abcdefgh1"}).status_code == 410
    assert c.get("/api/wallet").json()["hearts"] == before
    api.RIDS.clear()  # 서버 재시작으로 메모리 기록이 사라져도 원장이 같은 rid를 막는다
    assert c.post("/api/games", json={"rid": "abcdefgh2"}).status_code == 410
    assert c.get("/api/wallet").json()["hearts"] == before


def test_attend_and_buy_over_http(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    assert c.post("/api/wallet/attend").json()["coins"] == money.ATTEND
    assert c.post("/api/wallet/attend").status_code == 409
    assert c.post("/api/wallet/buy", json={"item": "hearts5"}).json()["detail"]["code"] == "gems"
    assert c.post("/api/wallet/buy", json={"item": "nope"}).status_code == 422
    for bad in ("abcdefg\u0000h", "a b c d e f"):  # 원장 text에 못 넣는 글자는 500이 아니라 422(Codex 26차)
        assert c.post("/api/wallet/buy", json={"item": "hearts5", "rid": bad}).status_code == 422
        assert c.post("/api/games", json={"rid": bad}).status_code == 422
    c.headers.pop("x-csrf")
    assert c.post("/api/wallet/attend").status_code == 403


def test_logged_in_wallet_read_checks_in_once_a_day(outbox, fast_hash):
    """접속만 해도 출석(11-27 사용자) — 로그인한 앱 계정이 그날 처음 잔고를 읽으면. 두 번째부터는 잔고만.
    웹(쿠키)은 GET에 CSRF 검사가 없어 남의 사이트가 이동만 시켜도 출석되므로 하지 않는다(리뷰 1차)"""
    from fastapi.testclient import TestClient

    from kumoniji.api import app

    from .helpers import ORIGIN

    c = browser()
    assert c.get("/api/wallet").status_code == 401  # 로그인 안 하면 출석도 없다
    signed_up(c, outbox)
    login(c)
    web = c.get("/api/wallet").json()
    assert "attended_now" not in web and web["coins"] == 0
    a = TestClient(app, base_url=ORIGIN, headers={"x-kumoniji-client": "app"})
    a.headers["authorization"] = f"Bearer {login(a).json()['access']}"
    first = a.get("/api/wallet").json()
    assert first["attended_now"] is True and first["coins"] == money.ATTEND and first["attend"]["claimed"]
    again = a.get("/api/wallet").json()
    assert "attended_now" not in again and again["coins"] == money.ATTEND
    assert a.post("/api/wallet/attend").status_code == 409


def test_failed_single_record_is_retried_in_background(outbox, fast_hash, monkeypatch):
    from kumoniji import api

    monkeypatch.setattr(api, "RECORD_RETRY", (0.1,))
    real, calls = store.finish_game, []

    def flaky(*args, **kw):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("DB 잠깐 끊김")
        return real(*args, **kw)

    monkeypatch.setattr(store, "finish_game", flaky)
    c = browser()
    signed_up(c, outbox)
    login(c)
    v = c.post("/api/games").json()
    while v["winner"] is None:
        v = c.post(f"/api/games/{v['id']}/moves", json={"tiles": v["moves"][0] if v["moves"] else []}).json()
    assert "wallet" not in v  # 첫 기록은 실패 — 결과는 그대로 보여 준다
    for _ in range(50):
        if api.GAMES[v["id"]].recorded:
            break
        time.sleep(0.1)
    assert c.get("/api/wallet").json()["missions"]["counts"]["games"] == 1


def _four(prefix):
    return [make_account(email=f"{prefix}{i}@x.com", nickname=f"{prefix}{i}") for i in range(4)]


def test_multi_start_takes_one_heart_from_each_of_four_once(database):
    """판이 잡히면 네 명의 하트를 한 번에 1개씩(ADR-0024 B안). 같은 판으로 다시 불러도 한 번만."""
    four, now = _four("ms"), time.time()
    with db.tx() as c:
        assert store.start_multi(c, four, "multi:t1", now, stake=False) == {}
        assert store.start_multi(c, four, "multi:t1", now, stake=False) == {}  # 응답을 못 받아 다시 시도
        assert [store.snapshot(c, a, now)["hearts"] for a in four] == [9, 9, 9, 9]


def test_multi_start_with_one_short_takes_nothing_from_anyone(database):
    four, now = _four("short"), time.time()
    with db.tx() as c:
        store.snapshot(c, four[2], now)  # 지갑을 만든다
        c.execute("UPDATE wallets SET hearts = 0 WHERE account_id = %s", (four[2],))
        assert store.start_multi(c, four, "multi:t2", now, stake=False) == {four[2]: "no_heart"}
        assert [store.snapshot(c, a, now)["hearts"] for a in four] == [10, 10, 0, 10]  # 아무도 안 빠짐


def test_auto_match_start_needs_the_minimum_stake_but_room_does_not(database):
    four, now = _four("stake"), time.time()
    with db.tx() as c:
        for a in four:
            store.snapshot(c, a, now)
        c.execute("UPDATE wallets SET coins = %s WHERE account_id = ANY(%s)", (money.MIN_STAKE, four[1:]))
        assert store.start_multi(c, four, "multi:t3", now, stake=True) == {four[0]: "low_coins"}
        assert store.start_multi(c, four, "multi:t4", now, stake=False) == {}  # 친구방은 판돈을 안 본다


def test_multi_start_from_ten_starts_refill_now(database):
    """10개에서 쓰면 충전 시계는 판이 잡힌 지금부터 — 10분 뒤에 다시 10."""
    four = _four("ten")
    now = float(int(time.time()) + 2)  # 정수(timestamptz 반올림 회피), 지갑을 만든 시각보다 뒤
    with db.tx() as c:
        assert store.start_multi(c, four, "multi:t5", now, stake=False) == {}
        assert store.snapshot(c, four[0], now + 599)["hearts"] == 9
        assert store.snapshot(c, four[0], now + 600)["hearts"] == 10


def fail_ledger_check_once(monkeypatch):
    """원장 확인(SELECT … FROM ledger) 한 번만 DB 오류로 — 로그인 확인 등 다른 조회는 그대로."""
    real, fails = api.db.tx, [1]

    class Conn:
        def __init__(self, c):
            self.c = c

        def execute(self, sql, *args):
            if fails and "FROM ledger" in sql:
                fails.pop()
                raise RuntimeError("DB 일시 장애")
            return self.c.execute(sql, *args)

        def __getattr__(self, name):
            return getattr(self.c, name)

    @contextmanager
    def tx():
        with real() as c:
            yield Conn(c)

    monkeypatch.setattr(api.db, "tx", tx)


def test_new_game_whose_heart_commit_reply_was_lost_opens_on_the_same_rid(outbox, fast_hash, monkeypatch):
    """하트 쓰기가 커밋된 뒤 응답만 끊기면(서버는 살아 있음) 같은 rid로 다시 보낼 때 하트를 다시 쓰지 않고 판을 연다
    — 전엔 rid를 잊어 410이 나 하트만 잃었다(리뷰 지적)."""
    c = browser()
    signed_up(c, outbox)
    login(c)
    real, calls = api.store.use_heart, []

    def flaky(x, *args, **kw):
        calls.append(1)
        out = real(x, *args, **kw)
        if len(calls) == 1:
            x.commit()
            raise RuntimeError("응답 끊김")
        return out

    monkeypatch.setattr(api.store, "use_heart", flaky)
    with pytest.raises(api.HeartUnknown):
        c.post("/api/games", json={"rid": "lostreply1"})
    fail_ledger_check_once(monkeypatch)  # 첫 재시도는 원장 확인부터 실패 — 그래도 '모름'은 남아야 한다(리뷰 지적)
    with pytest.raises(api.HeartUnknown):
        c.post("/api/games", json={"rid": "lostreply1"})
    r = c.post("/api/games", json={"rid": "lostreply1"})
    assert r.status_code == 200 and c.get("/api/wallet").json()["hearts"] == 9
    assert c.post("/api/games", json={"rid": "lostreply1"}).json()["id"] == r.json()["id"]  # 그 뒤로는 같은 판


def test_ledger_check_failure_before_charging_does_not_make_an_old_rid_free(outbox, fast_hash, monkeypatch):
    """재시작 뒤 이미 쓴 rid가 다시 왔는데 원장 확인부터 실패하면, 다음 요청이 옛 하트 기록을 이번 것으로 착각해 공짜 판을
    열면 안 된다 — 하트를 쓰기 전 오류는 '모름'이 아니라 '안 씀'이다(리뷰 지적)."""
    c = browser()
    signed_up(c, outbox)
    login(c)
    assert c.post("/api/games", json={"rid": "usedbefore1"}).status_code == 200
    api.RIDS.clear()  # 서버 재시작
    fail_ledger_check_once(monkeypatch)
    with pytest.raises(RuntimeError):
        c.post("/api/games", json={"rid": "usedbefore1"})
    before = c.get("/api/wallet").json()["hearts"]
    assert c.post("/api/games", json={"rid": "usedbefore1"}).status_code == 410
    assert c.get("/api/wallet").json()["hearts"] == before


def test_wallet_lock_wait_is_bounded(outbox, fast_hash):
    """지갑 행 잠금을 누가 오래 쥐고 있어도 기다림은 store.LOCK_WAIT로 끝난다 — 멀티 지갑 DB 자리(1개)를 붙잡고 있으면
    상관없는 사람의 입장·판 끝 기록까지 막힌다(리뷰 지적). 끝나면 부른 쪽이 다시 하거나 busy로 답한다."""
    import psycopg

    a = make_account()
    with db.tx() as holder:
        store.snapshot(holder, a, time.time())  # 잠금을 쥔 채로
        start = time.monotonic()
        with pytest.raises(psycopg.errors.LockNotAvailable), db.tx() as c:
            store.snapshot(c, a, time.time())
        assert time.monotonic() - start < 10


def test_resume_waits_for_the_wallet_lock_before_reading_the_ledger(outbox, fast_hash):
    """앞선 같은 rid 요청의 커밋이 아직 끝나지 않았을 때(지갑 잠금을 쥔 채) 재시도가 오면, 잠금을 먼저 기다린 뒤 원장을
    봐야 그 하트를 보고 판을 연다 — 원장을 먼저 읽으면 놓치고 402가 난다(리뷰 지적)."""
    import threading

    c = browser()
    signed_up(c, outbox)
    login(c)
    with db.tx() as x:
        a = x.execute("SELECT id FROM accounts WHERE email = 'me@x.com'").fetchone()["id"]
        x.execute(
            """INSERT INTO wallets (account_id, hearts) VALUES (%s, 1)
               ON CONFLICT (account_id) DO UPDATE SET hearts = 1, hearts_at = now()""",
            (a,),
        )
    api.RIDS[(a, "inflight01")] = api.UNKNOWN
    out = {}
    with db.tx() as holder:
        assert store.use_heart(holder, a, time.time(), "new:inflight01")  # 앞선 요청: 쓰고 아직 커밋 전
        t = threading.Thread(target=lambda: out.setdefault("r", c.post("/api/games", json={"rid": "inflight01"})))
        t.start()
        time.sleep(0.5)  # 재시도가 잠금에서 기다리는 중
    t.join(10)  # holder 커밋 → 재시도가 원장을 보고 판을 연다
    assert out["r"].status_code == 200 and c.get("/api/wallet").json()["hearts"] == 0


def _delete(a: int) -> None:
    """탈퇴와 같은 순서 — 계정 행을 먼저 표시하고 화폐 기록을 지운다(accounts.service._purge)."""
    from kumoniji.accounts import service

    with db.tx() as c:
        c.execute("UPDATE accounts SET deleted_at = now() WHERE id = %s", (a,))
        service._purge(c, a)


def test_game_end_skips_a_player_who_deleted_mid_game_and_settles_the_rest(database):
    """판 중 탈퇴한 사람의 지갑·원장·일일 기록을 판 끝 정산이 되살리지 않고, 나머지는 미션만 기록된다(판돈은 없던 일, 리뷰 지적).
    탈퇴한 사람의 '이미 기록함' 표식이 지워진 뒤 재시도가 와도 다시 정산하지 않는다."""
    ids = [make_account(email=f"d{i}@x.com", nickname=f"d{i}") for i in range(4)]
    with db.tx() as c:
        for a in ids:
            c.execute("INSERT INTO wallets (account_id, coins) VALUES (%s, 10000)", (a,))
    players = [P(ids[0], 1, 60, left=0), P(ids[1], 2, -10), P(ids[2], 3, -20), P(ids[3], 4, -30)]
    _delete(ids[3])
    with db.tx() as c:
        store.finish_game(c, "g1", players, time.time(), stake=True)
        for table in ("wallets", "ledger", "daily"):
            assert c.execute(f"SELECT count(*) AS n FROM {table} WHERE account_id = %s", (ids[3],)).fetchone()["n"] == 0
        first = [store.snapshot(c, a, time.time())["coins"] for a in ids[:3]]
        assert c.execute("SELECT count(*) AS n FROM ledger WHERE kind = 'stake' AND ref = 'g1'").fetchone()["n"] == 0
    # 탈퇴자가 있으면 판돈은 없던 일(걷어서 버리거나 남은 사람에게 몰아주지 않음), 미션 보상은 그대로
    assert first == [10000 + 2 * money.MISSION, 10000 + money.MISSION, 10000 + money.MISSION]
    _delete(ids[0])  # 맨 앞 사람(옛 표식 자리)까지 탈퇴한 뒤 재시도
    with db.tx() as c:
        store.finish_game(c, "g1", players, time.time(), stake=True)
        assert [store.snapshot(c, a, time.time())["coins"] for a in ids[1:3]] == first[1:]


def test_deleted_account_gets_no_new_wallet_and_aborts_a_multi_start(database):
    ids = [make_account(email=f"e{i}@x.com", nickname=f"e{i}") for i in range(4)]
    _delete(ids[2])
    with db.tx() as c:
        with pytest.raises(store.AccountGone):
            store.snapshot(c, ids[2], time.time())
    with db.tx() as c:
        assert store.start_multi(c, ids, "multi:gone1", time.time(), stake=False) == {ids[2]: "no_heart"}
        assert c.execute("SELECT count(*) AS n FROM ledger WHERE ref = 'multi:gone1'").fetchone()["n"] == 0


def test_single_record_retry_stops_when_the_account_was_deleted(outbox, fast_hash, monkeypatch):
    """싱글 판 끝 기록이 실패해 재시도를 기다리는 사이 탈퇴하면, 재시도는 기록할 것 없음으로 끝난다 — 남겨 두면 영영 다시 한다(리뷰 지적)."""
    monkeypatch.setattr(api, "RECORD_RETRY", (0.1,))
    real, calls = store.finish_game, []

    def fail_then_deleted(c, ref, players, *args, **kw):
        calls.append(1)
        if len(calls) == 1:
            a = next(p["account"] for p in players if p["account"] is not None)
            _delete(a)
            raise RuntimeError("DB 잠깐 끊김")
        return real(c, ref, players, *args, **kw)

    monkeypatch.setattr(store, "finish_game", fail_then_deleted)
    c = browser()
    signed_up(c, outbox)
    login(c)
    v = c.post("/api/games").json()
    while v["winner"] is None:
        v = c.post(f"/api/games/{v['id']}/moves", json={"tiles": v["moves"][0] if v["moves"] else []}).json()
    for _ in range(50):
        if not api.RETRY:
            break
        time.sleep(0.1)
    assert api.RETRY == {}


def test_account_lock_wait_is_bounded_too(database):
    """탈퇴 처리 등이 계정 행을 오래 잠가도 지갑 작업의 첫 잠금(store.live)은 LOCK_WAIT 뒤 끝난다(리뷰 지적)."""
    import psycopg

    a = make_account()
    with db.tx() as holder:
        holder.execute("UPDATE accounts SET nickname = nickname WHERE id = %s", (a,))  # 계정 행 잠금을 쥔 채로
        start = time.monotonic()
        with pytest.raises(psycopg.errors.LockNotAvailable), db.tx() as c:
            store.live(c, [a])
        assert time.monotonic() - start < 10


def test_rid_cache_trim_keeps_unknown_and_creating_entries(outbox, fast_hash, monkeypatch):
    """rid 기록이 한도를 넘어 오래된 것을 지울 때 '모름'·만드는 중은 남긴다 — 밀려나면 낸 하트로 판을 못 연다(리뷰 지적)."""
    monkeypatch.setattr(api, "MAX_RIDS", 2)
    c = browser()
    signed_up(c, outbox)
    login(c)
    api.RIDS.clear()
    api.RIDS[(0, "unknownold")] = api.UNKNOWN  # 가장 오래된 '모름'
    api.RIDS[(0, "creatingold")] = None  # 만드는 중
    for i in range(3):
        assert c.post("/api/games", json={"rid": f"trimtest{i}"}).status_code == 200
    assert api.RIDS.get((0, "unknownold")) == api.UNKNOWN
    assert (0, "creatingold") in api.RIDS and api.RIDS[(0, "creatingold")] is None


def test_snapshot_version_grows_in_lock_order(database):
    """스냅숏의 v는 지갑 행을 잠근 뒤 찍어, 같은 계정이면 나중에 커밋된 것이 더 크다 — 앱이 옛 응답을 버리는 기준."""
    a = make_account()
    with db.tx() as c:
        first = store.snapshot(c, a, time.time())
    with db.tx() as c:
        after = store.attend(c, a, time.time())
    assert after["v"] > first["v"]


def test_request_for_another_account_is_refused_before_spending(outbox, fast_hash):
    """웹은 로그인 쿠키를 탭끼리 같이 쓴다 — A 화면이 보낸 요청(x-kumoniji-account: A)이 B 세션으로 오면 쓰지 않고 409."""
    c = browser()
    signed_up(c, outbox)
    login(c)
    me = c.get("/api/auth/me").json()["id"]
    r = c.post("/api/games", json={"rid": "othertab1"}, headers={"x-kumoniji-account": str(me + 1000)})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "account_changed"
    assert c.get("/api/wallet").json()["hearts"] == 10  # 하트를 안 썼다
    assert c.post("/api/games", json={"rid": "othertab2"}, headers={"x-kumoniji-account": str(me)}).status_code == 200


def test_snapshot_version_keeps_growing_when_the_clock_steps_back(database, monkeypatch):
    a = make_account()
    clock = iter([1000.0, 999.0, 998.5])
    monkeypatch.setattr(store.time, "time", lambda: next(clock))
    with db.tx() as c:
        vs = [store.snapshot(c, a, 1000.0)["v"] for _ in range(3)]
    assert vs[0] < vs[1] < vs[2]


def test_snapshot_version_keeps_growing_after_the_db_is_restored_from_a_backup(database):
    a = make_account()
    with db.tx() as c:
        store.snapshot(c, a, 1000.0)
        seen = store.snapshot(c, a, 1000.0)["v"]
        c.execute("UPDATE wallets SET v = 1 WHERE account_id = %s", (a,))  # 백업으로 되돌려 번호가 옛 값이 됨
        assert store.snapshot(c, a, 1000.0)["v"] > seen
