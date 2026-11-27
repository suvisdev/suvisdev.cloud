"""화폐 DB. 잔고 행은 FOR UPDATE로 잠그고, 증감은 원장(ledger)에 먼저 넣어 같은 kind+ref가 두 번 들어가지 않게 한다."""

import secrets
import time
from datetime import datetime, timezone

from psycopg.types.json import Jsonb

from . import missions, money


def _dt(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, timezone.utc)


LOCK_WAIT = "3s"  # 계정·지갑 행 잠금을 기다리는 상한 — 넘으면 LockNotAvailable(부른 쪽이 다시 하거나 busy)


class AccountGone(Exception):
    """탈퇴한 계정의 지갑을 건드리려 함 — 지갑을 새로 만들지 않는다(탈퇴 파기, accounts.service._purge)."""


def live(c, accounts: list[int]) -> set[int]:
    """탈퇴하지 않은 계정. 계정 행을 공유 잠금해 탈퇴(계정 행을 먼저 고친 뒤 지갑을 지움)와 차례로 돈다.
    잠금은 LOCK_WAIT까지만 기다린다 — 지갑 작업은 늘 여기서 처음 잠그므로 이 트랜잭션의 뒤 잠금(_wallet)도 같은 상한(리뷰 지적)."""
    c.execute(f"SET LOCAL lock_timeout = '{LOCK_WAIT}'")
    rows = c.execute(
        "SELECT id FROM accounts WHERE id = ANY(%s) AND deleted_at IS NULL ORDER BY id FOR SHARE", (sorted(accounts),)
    )
    return {r["id"] for r in rows}



def _wallet(c, a: int, now: float) -> dict:
    """잔고 행을 (없으면 만들고) 잠그고 하트 충전을 반영한다(원장에 regen). 10 이상이면 충전 기준 시각이 지금이 된다.
    잠금은 LOCK_WAIT까지만 기다린다 — 오래 쥔 잠금 하나가 멀티 지갑 DB 자리(1개)를 붙잡아 상관없는 사람까지 막지 않게(리뷰 지적)."""
    if not live(c, [a]):  # 잠금 상한도 여기서. 탈퇴 뒤 늦게 온 쓰기가 지갑·원장을 되살리지 않게(리뷰 지적)
        raise AccountGone(a)
    c.execute("INSERT INTO wallets (account_id) VALUES (%s) ON CONFLICT DO NOTHING", (a,))
    w = c.execute("SELECT * FROM wallets WHERE account_id = %s FOR UPDATE", (a,)).fetchone()
    hearts, since = money.regen(w["hearts"], w["hearts_at"].timestamp(), now)
    if (hearts, since) != (w["hearts"], w["hearts_at"].timestamp()):
        if hearts != w["hearts"]:  # 충전 기준 시각은 충전마다 뒤로만 가므로 ref로 겹치지 않는다
            c.execute(
                "INSERT INTO ledger (account_id, kind, ref, hearts) VALUES (%s, 'regen', %s, %s)",
                (a, _dt(since).isoformat(), hearts - w["hearts"]),
            )
        c.execute("UPDATE wallets SET hearts = %s, hearts_at = %s WHERE account_id = %s", (hearts, _dt(since), a))
        w = {**w, "hearts": hearts, "hearts_at": _dt(since)}
    return w


def _apply(c, a: int, kind: str, ref: str, coins=0, gems=0, hearts=0) -> bool:
    """원장에 넣고 잔고에 반영. 이미 있던 kind+ref면 아무것도 안 하고 False. 0 아래로는 안 내려간다(CHECK)."""
    row = c.execute(
        """INSERT INTO ledger (account_id, kind, ref, coins, gems, hearts) VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING RETURNING 1""",
        (a, kind, ref, coins, gems, hearts),
    ).fetchone()
    if row:
        c.execute(
            "UPDATE wallets SET coins = coins + %s, gems = gems + %s, hearts = hearts + %s WHERE account_id = %s",
            (coins, gems, hearts, a),
        )
    return bool(row)


def _counts(c, a: int, day: str) -> dict:
    d = c.execute("SELECT counts FROM daily WHERE account_id = %s AND day = %s", (a, day)).fetchone()
    return d["counts"] if d else {}


def snapshot(c, a: int, now: float) -> dict:
    w = _wallet(c, a, now)
    day = missions.day_of(now)
    counts = _counts(c, a, day)
    done = missions.done(counts)
    nxt = None if w["hearts"] >= money.HEART_MAX else w["hearts_at"].timestamp() + money.HEART_EVERY
    return {
        # 순서 번호 — 잠근 지갑 행에서 올린다(004). 앱은 이보다 옛 것을 버린다(응답 도착 순서로는 서버 처리 순서를 알 수
        # 없음, 11-26 앱 리뷰). ponytail: 복원과 함께 서버 시계까지 과거로 돌아가면 남는 틈 — 그때는 wallets.v를 손으로 올린다
        "v": c.execute(
            "UPDATE wallets SET v = greatest(v + 1, (extract(epoch FROM clock_timestamp()) * 1000000)::bigint)"
            " WHERE account_id = %s RETURNING v",
            (a,),
        ).fetchone()["v"],
        "now": time.time(),  # 서버의 실제 시각("t"는 소켓 메시지 종류 키라 피함) — 앱이 충전·자정 계산에 쓴다(v는 순서 번호라 시계가 되감기면 실제보다 앞설 수 있음, 리뷰 26차)
        "coins": w["coins"],
        "gems": w["gems"],
        "hearts": w["hearts"],
        "next_heart": nxt,
        "attend": {
            "day": day,
            "streak": w["attend_streak"],
            "claimed": str(w["attend_day"]) == day,
            # 지금 출석하면 이어질 날 수 — 7의 배수면 보상이 다르다(앱 버튼 안내, 리뷰 27차). attend()와 같은 계산
            "next": w["attend_streak"] + 1 if str(w["attend_day"]) == missions.day_of(now - 86400) else 1,
        },
        "missions": {"all": missions.MISSIONS, "done": done, "counts": counts, "bonus": len(done) >= money.MISSION_NEED},
    }


def use_heart(c, a: int, now: float, ref: str | None = None) -> bool:
    """하트가 있으면 1개 쓰고 True(0 아래로는 안 감). 10개에서 쓰면 충전은 지금부터(_wallet이 기준 시각을 맞춤)."""
    if _wallet(c, a, now)["hearts"] < 1:
        return False
    return _apply(c, a, "heart", ref or f"use:{secrets.token_hex(8)}", hearts=-1)


def start_multi(c, accounts: list[int], game: str, now: float, *, stake: bool) -> dict[int, str]:
    """멀티 판이 잡힘: 네 명의 하트를 한 트랜잭션에서 1개씩 쓴다(ADR-0024 B안, 11-25 사용자).
    모자란 사람이 있으면 아무도 안 쓰고 {계정: 이유}를 돌려준다 — no_heart(하트 0), low_coins(자동 매칭인데 판돈 MIN_STAKE 미만).
    빈 dict면 성공. 같은 판(game)으로 다시 불러도 원장이 이미 있으면 그대로 성공(응답을 못 받아 다시 시도한 경우).
    지갑 행은 계정 번호 순으로 잠근다 — 두 판이 같은 사람을 반대 순서로 잠가 서로 기다리지 않게."""
    order = sorted(accounts)
    alive = live(c, order)
    if gone := [a for a in order if a not in alive]:  # 그사이 탈퇴 — 이미 쓴 판(재시도)이 아니면 아무도 안 쓰고 거둔다
        paid = c.execute(
            "SELECT count(*) AS n FROM ledger WHERE kind = 'heart' AND ref = %s AND account_id = ANY(%s)",
            (game, sorted(alive)),
        ).fetchone()["n"]
        return {} if alive and paid == len(alive) else {a: "no_heart" for a in gone}
    wallets = {a: _wallet(c, a, now) for a in order}  # 잠금 + 충전 반영
    done = c.execute(
        "SELECT count(*) AS n FROM ledger WHERE kind = 'heart' AND ref = %s AND account_id = ANY(%s)", (game, order)
    ).fetchone()["n"]
    if done == len(order):
        return {}
    if done:  # 한 트랜잭션이라 일부만 있을 수 없다 — 있으면 버그, 판을 열지 않는다
        raise RuntimeError(f"멀티 하트 일부만 쓰임: {game}")
    short = {}
    for a, w in wallets.items():
        if w["hearts"] < 1:
            short[a] = "no_heart"
        elif stake and w["coins"] < money.MIN_STAKE:
            short[a] = "low_coins"
    if short:
        return short
    for a in order:
        _apply(c, a, "heart", game, hearts=-1)  # 10개에서 쓰면 충전은 지금부터(_wallet이 방금 기준 시각을 now로)
    return {}


def finish_game(c, ref: str, players: list[dict], now: float, *, stake: bool, day_at: float | None = None) -> None:
    """판 끝: (자동 매칭이면) 판돈, 그날 미션 누적·보상. 같은 ref는 한 번만(원장 'game' 표식).
    하트는 여기서 안 쓴다 — 싱글은 판을 열 때, 멀티는 들어갈 때(대기열·방 시작) 쓴다.
    now는 지금(하트 충전 계산), day_at은 판이 끝난 시각(미션 날짜 — 재시도가 자정을 넘겨도 그날 몫). 없으면 now.
    players[i] = {"account": id|None, "stats", "rank", "left", "points"} — stake=True면 네 자리 모두 계정이어야 한다."""
    people = sorted((p for p in players if p["account"] is not None), key=lambda p: p["account"])
    alive = live(c, [p["account"] for p in people])  # 판 중 탈퇴한 사람은 기록하지 않는다(리뷰 지적) — 나머지는 미션만 그대로
    # 탈퇴자가 있으면 판돈은 없던 일로 — 그 사람이 받을 몫을 남은 사람에게 주거나 걷어서 버리면 '걷힌 만큼 나눈다'가 깨진다(리뷰 지적)
    stake = stake and len(alive) == len(people)
    people = [p for p in people if p["account"] in alive]
    for p in people:  # 잠그는 순서를 고정해 교착 방지
        _wallet(c, p["account"], now)
    # 이미 기록한 판(재시도)이면 끝. 표식은 모두에게 — 한 사람에게만 두면 그 사람이 탈퇴해 원장이 지워진 뒤 재시도가 다시 정산한다
    if not people or not all([_apply(c, p["account"], "game", ref) for p in people]):
        return
    if stake:
        bal = [_wallet(c, p["account"], now)["coins"] for p in players]
        for p, delta in zip(players, money.stake([p["points"] for p in players], bal)):
            _apply(c, p["account"], "stake", ref, coins=delta)
    day = missions.day_of(day_at or now)
    for p in people:
        a = p["account"]
        before = _counts(c, a, day)
        counts = missions.add_game(before, p["stats"], p["rank"], p["left"], p["points"])
        c.execute(
            """INSERT INTO daily (account_id, day, counts) VALUES (%s, %s, %s)
               ON CONFLICT (account_id, day) DO UPDATE SET counts = EXCLUDED.counts""",
            (a, day, Jsonb(counts)),
        )
        after = missions.done(counts)
        for m in set(after) - set(missions.done(before)):
            _apply(c, a, "mission", f"{day}:{m}", coins=money.MISSION)
        if len(after) >= money.MISSION_NEED:
            _apply(c, a, "bonus", day, coins=money.MISSION_BONUS)


def attend(c, a: int, now: float) -> dict:
    """그날 출석. 이미 받았으면 LookupError("attended"). 이어진 날 수가 7의 배수인 날은 판돈을 더 주고 보석도."""
    w = _wallet(c, a, now)
    day = missions.day_of(now)
    if w["attend_day"] is not None and str(w["attend_day"]) >= day:  # 자정 직전 요청이 늦게 잠금을 얻어도 날짜를 되돌리지 않는다
        raise LookupError("attended")
    streak = w["attend_streak"] + 1 if str(w["attend_day"]) == missions.day_of(now - 86400) else 1
    seventh = streak % 7 == 0
    c.execute("UPDATE wallets SET attend_day = %s, attend_streak = %s WHERE account_id = %s", (day, streak, a))
    _apply(
        c, a, "attend", day,
        coins=money.ATTEND_7TH if seventh else money.ATTEND,
        gems=money.ATTEND_7TH_GEMS if seventh else 0,
    )  # fmt: skip
    return snapshot(c, a, now)


def buy(c, a: int, item: str, now: float, rid: str | None = None) -> dict:
    """보석으로 상품 구매. 보석 부족 LookupError("gems"), 없는 상품 KeyError.
    rid가 있으면 원장 참조로 — 같은 요청을 다시 보내면 사지 않고 지금 잔고만 돌려준다."""
    price, gives = money.SHOP[item]
    ref = f"{item}:{rid or secrets.token_hex(8)}"
    w = _wallet(c, a, now)  # 지갑 행을 잠가 같은 rid가 동시에 와도 하나씩
    if rid and c.execute(
        "SELECT 1 FROM ledger WHERE account_id = %s AND kind = 'buy' AND ref = %s", (a, ref)
    ).fetchone():
        return snapshot(c, a, now)
    if w["gems"] < price:
        raise LookupError("gems")
    _apply(c, a, "buy", ref, gems=-price, **gives)
    return snapshot(c, a, now)


def players_of(g, accounts: list[int | None]) -> list[dict]:
    """끝난 판(Game)을 finish_game의 players로. 1등은 판을 끝낸 사람, 나머지는 정산 점수 순."""
    pts = g.settlement()
    order = sorted(range(4), key=lambda i: (i != g.winner, -pts[i]))
    return [
        {"account": a, "stats": g.stats[i], "rank": order.index(i) + 1, "left": len(g.hands[i]), "points": pts[i]}
        for i, a in enumerate(accounts)
    ]
