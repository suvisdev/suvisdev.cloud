# 계획 D — 화폐(판돈·하트·보석)·출석·미션

**Goal:** 계정마다 판돈·하트·보석 잔고를 두고, 자동 매칭 판은 1점당 50 판돈을 주고받으며, 출석·일일 미션으로 판돈을 가볍게 준다.

**Architecture:** 서버 권위. 잔고와 모든 증감은 Postgres(`wallets` + 원장 `ledger`)에 기록하고, 원장의 `(account_id, kind, ref)` 고유 제약으로 같은 판·같은 보상이 두 번 들어가지 않게 한다. 정산 금액 계산·미션 판정은 DB 없는 순수 함수(`wallet/money.py`, `wallet/missions.py`)이고, DB 쓰기는 `wallet/store.py` 한 곳에서 한다. 판 기록에 필요한 통계(5장 조합 수 등)는 `Game`이 판 중에 모은다.

**Tech Stack:** FastAPI·psycopg 3(기존 `accounts/db.py` 풀·번호 마이그레이션), Flutter(기존 `api.dart`·`l10n` 4개 언어).

## Global Constraints

- 결정(11-24 사용자): **1점당 50 판돈**. 판돈은 **자동 매칭 판에서만** 주고받는다 — 싱글·친구방은 점수만.
- 결정(11-24 사용자): 처음 큰 지급·파산 구제 없음("도박 사이트 같다"). 판돈은 **출석·미션으로 가볍게**, 나머지는 보석 구매·광고.
- 결정(11-24 사용자): 출석 하루 200, 7일째 500. 미션 하나 100. 광고 1회 100(하루 5회 — 광고는 앱에 광고 SDK가 붙을 때, 이 계획 밖).
- 결정(11-24 사용자): 일일 미션 **10개 고정, 5개 깨면 그날 완료**. 목록은 아래 표 그대로.
- 결정(기획 PRODUCT.md §4): 하트는 판 참여마다 1개(싱글·멀티), 10분에 1개씩 최대 10개까지 자동 충전. 구매로 얻은 하트는 10을 넘어 쌓인다(초안 E2).
- **결제는 붙이지 않는다**(SPEC: 유료 재화·판돈 결제 전 게임위 문의). 보석은 잔고·원장·사용처만 만들고, 들어오는 길은 출석 7일째뿐.
- 환전·송금 기능은 만들지 않는다. 화면 표기는 돈이 아니라 "판돈"(기획 RULES.md §5).
- 응답·문구는 한·영·일·중(간체) 4개 언어.

### Claude가 정한 기본값(바꾸려면 사용자에게 — 숫자는 `wallet/money.py` 상수 한 곳)

| 값 | 기본 | 이유 |
|---|---|---|
| 처음 잔고 | 판돈 0 · 하트 10 · 보석 0 | 큰 지급 없음(사용자). 하트는 기획대로 가득 |
| 자동 매칭 입장 최소 판돈 | 500(=10점) | 잃을 것이 하나도 없는 사람이 들어와 공짜로 버티지 않게. 출석·미션 하루치로 넘는다 |
| 판돈이 모자라면 | 잔고까지만 낸다(0 아래 없음). 받는 사람은 실제로 걷힌 만큼을 점수 비율로 나눠 받는다 | 빚 없음 — 기획 [결정 I] 칩 부족 처리 |
| 7일째 출석 보석 | 10 | 기획 "출석(조금)" |
| 상점 | 보석 10 → 하트 5 / 보석 10 → 판돈 1,000 | 사용처가 있어야 틀을 시험할 수 있음 |
| 미션 5개 완료 보너스 | 300 | 사용자 확인 대기(11-24 보고에 적음) |
| 하루 누적 점수 미션 기준 | 그날 판에서 얻은 점수(+만) 합 30점 | 사용자 확인 대기 |
| 날짜 기준 | 한국 시간 자정(Asia/Seoul) | 출시 순서가 한국 웹 먼저 |
| 멀티 하트 | 판이 잡히는 순간 네 명 것을 한 트랜잭션에서 쓴다(B안). 입장 때는 읽기만, 모자란 사람만 빠지고 나머지는 대기 순서 유지. 하트는 0이 최하 | 11-25 사용자 결정(ADR-0024): 판 끝에 빼면 싱글로 마지막 하트를 써 멀티가 공짜, 예약은 상태가 많음 |

### 일일 미션 10개(사용자 확정)

| id | 미션 | 판정(그날 누적) |
|---|---|---|
| `games5` | 5판 하기 | 끝난 판 ≥ 5 |
| `games10` | 10판 하기 | 끝난 판 ≥ 10 |
| `wins2` | 1등 2번 | 1등 ≥ 2 |
| `low3` | 손패 3장 이하로 판 끝내기 | 판 끝날 때 내 손패 ≤ 3인 판 ≥ 1 |
| `five3` | 5장 조합 3번 내기 | 낸 5장 조합 ≥ 3 |
| `triple2` | 트리플 2번 내기 | 낸 트리플 ≥ 2 |
| `today` | 오늘의 무늬로 바퀴 가져가기 | 오늘의 무늬가 든 패로 바퀴를 가져간 횟수 ≥ 1 |
| `score30` | 하루 누적 점수 30점 | 그날 판 점수 증감 중 +만 합 ≥ 30 |
| `oddeven` | 홀짝 내기 | 홀짝류(홀짝·같은색홀짝·같은모양홀짝) ≥ 1 |
| `fullhouse` | 풀하우스 내기 | 풀하우스 ≥ 1 |

싱글·친구방·자동 매칭 판 모두 미션에 센다(보상은 하루 상한이 있으니 싱글로 채워도 됨).

---

## 파일 구조

| 파일 | 역할 |
|---|---|
| `server/kumoniji/game.py` (수정) | `Game.stats`: 자리별 판 통계 모으기 |
| `server/kumoniji/accounts/migrations/003_wallet.sql` (새) | `wallets`·`ledger`·`daily` 테이블 |
| `server/kumoniji/wallet/__init__.py` (새) | 빈 패키지 |
| `server/kumoniji/wallet/money.py` (새) | 상수, 하트 충전, 판돈 정산(순수) |
| `server/kumoniji/wallet/missions.py` (새) | 하루 날짜, 미션 판정(순수) |
| `server/kumoniji/wallet/store.py` (새) | DB 읽기·쓰기(잔고 잠금, 원장, 판 끝 기록, 출석, 구매) |
| `server/kumoniji/wallet/web.py` (새) | `/api/wallet` 라우터 |
| `server/kumoniji/api.py` (수정) | 싱글 판 시작 때 하트, 끝날 때 기록. 라우터 등록 |
| `server/kumoniji/multi/ws.py` (수정) | 입장 조건(하트·최소 판돈), 판 끝 기록 |
| `server/kumoniji/accounts/web.py` (수정) | `socket_session`이 잔고 스냅숏도 돌려줌 |
| `server/tests/test_wallet_money.py`·`tests/test_missions.py`·`tests/accounts/test_wallet.py` (새) | 테스트 |
| `app/lib/wallet.dart` (새) | 잔고 모델·API, 상단 잔고 막대, 출석·미션·상점 화면 |
| `app/lib/home_screen.dart`·`table_screen.dart` (수정) | 잔고 막대, 하트 없음 안내 |
| `app/lib/l10n/app_{ko,en,ja,zh}.arb` (수정) | 문구 |

---

### Task 1: 판 통계(`Game.stats`)

**Files:**
- Modify: `server/kumoniji/game.py` (`Game` 필드, `play`)
- Test: `server/tests/test_game.py`

**Interfaces:**
- Produces: `Game.stats: list[dict]` — 자리마다 `{"five": int, "triple": int, "oddeven": int, "fullhouse": int, "today": int}`. 판이 끝난 뒤 손패 수는 `len(g.hands[i])`, 등수 1등은 `g.winner`.

- [ ] **Step 1: 실패하는 테스트**

```python
# tests/test_game.py
from kumoniji.game import Game
from kumoniji.rules import parse

T = lambda text: [parse(x) for x in text.split()]  # parse는 한 장씩


def test_stats_count_combos_and_today_rounds():
    hands = [T("벚3 잎3 산3 솜5 솜6 솜7 솜8 솜9 잎13"), T("솜1 솜2"), T("잎1 잎2"), T("산1 산2")]
    g = Game(hands=hands, today="솜", turn=0)
    g.play(0, T("벚3 잎3 산3"))        # 트리플
    for s in (1, 2, 3):
        g.play(s, None)                     # 셋 다 패스 → 0번이 바퀴를 가져감(오늘의 무늬 없음)
    g.play(0, T("솜5 솜6 솜7 솜8 솜9"))  # 5장(스트레이트플러시)
    for s in (1, 2, 3):
        g.play(s, None)                     # 오늘의 무늬(솜)가 든 패로 가져감
    assert g.stats[0] == {"five": 1, "triple": 1, "oddeven": 0, "fullhouse": 0, "today": 1}
    assert g.stats[1] == {"five": 0, "triple": 0, "oddeven": 0, "fullhouse": 0, "today": 0}
```

- [ ] **Step 2: 실패 확인** — `pytest -q tests/test_game.py -k stats` → `AttributeError: 'Game' object has no attribute 'stats'`

- [ ] **Step 3: 구현**

```python
# game.py — Game 필드 끝에
    stats: list[dict] = field(
        default_factory=lambda: [{"five": 0, "triple": 0, "oddeven": 0, "fullhouse": 0, "today": 0} for _ in range(4)]
    )

# play(): 바퀴를 가져가는 분기(self.passes == n - 1) 안, 바닥을 비우기 전에
                if any(s == self.today for s, _ in self.table):
                    self.stats[self.last]["today"] += 1

# play(): 패를 낸 분기, 손패에서 뺀 뒤
            kind = classify(move)[0]
            st = self.stats[seat]
            st["five"] += len(move) == 5
            st["triple"] += kind == "트리플"
            st["oddeven"] += "홀짝" in kind
            st["fullhouse"] += kind == "풀하우스"
```
(`from .rules import classify` 추가. 마지막 패로 판이 끝나면 그 패도 위에서 세어진다.)

- [ ] **Step 4: 통과 확인** — `pytest -q tests/test_game.py tests/test_rules_cases.py` → 모두 PASS(규칙 사례는 그대로)

- [ ] **Step 5: 커밋** — `git commit -m "feat: 쿠모니지 판 통계 모으기"`(계획 D PR 하나에 Task 1~5를 함께 올린다)

---

### Task 2: 순수 계산 — 하트 충전·판돈 정산·미션 판정

**Files:**
- Create: `server/kumoniji/wallet/__init__.py`(빈 파일), `wallet/money.py`, `wallet/missions.py`
- Test: `server/tests/test_wallet_money.py`, `server/tests/test_missions.py`

**Interfaces:**
- Produces:
  - `money.POINT=50`, `MIN_STAKE=500`, `HEART_MAX=10`, `HEART_EVERY=600`, `ATTEND=200`, `ATTEND_7TH=500`, `ATTEND_7TH_GEMS=10`, `MISSION=100`, `MISSION_BONUS=300`, `MISSION_NEED=5`, `SHOP={"hearts5": (10, {"hearts": 5}), "coins1000": (10, {"coins": 1000})}`
  - `money.regen(hearts: int, since: float, now: float) -> tuple[int, float]` — (지금 하트, 다음 충전 기준 시각)
  - `money.stake(points: list[int], balances: list[int]) -> list[int]` — 판돈 증감(합 0)
  - `missions.MISSIONS: list[str]`(위 표 순서), `missions.day_of(ts: float) -> str`(`"2026-11-24"`), `missions.add_game(c: dict, seat_stats: dict, rank: int, left: int, points: int) -> dict`, `missions.done(c: dict) -> list[str]`

- [ ] **Step 1: 실패하는 테스트**

```python
# tests/test_wallet_money.py
from kumoniji.wallet import money


def test_regen_one_heart_per_ten_minutes_up_to_ten():
    assert money.regen(3, 0, 599) == (3, 0)
    assert money.regen(3, 0, 1300) == (5, 1200)          # 2개 차고 남은 100초는 다음 충전으로
    assert money.regen(9, 0, 10_000)[0] == 10            # 10에서 멈춤
    assert money.regen(12, 0, 10_000) == (12, 10_000)    # 산 하트는 10을 넘어 그대로, 충전 없음


def test_stake_is_points_times_50_and_zero_sum():
    assert money.stake([60, -10, -20, -30], [10**6] * 4) == [3000, -500, -1000, -1500]


def test_stake_never_takes_more_than_balance_and_winners_share_what_was_paid():
    # 3번은 1,500을 내야 하지만 200뿐 → 200만. 받는 사람(0번)은 실제로 걷힌 500+1000+200
    assert money.stake([60, -10, -20, -30], [0, 10**6, 10**6, 200]) == [1700, -500, -1000, -200]
    # 받는 사람이 둘이면 점수 비율로, 남는 1은 많이 받는 쪽에
    out = money.stake([20, 10, -15, -15], [0, 0, 10**6, 101])
    assert sum(out) == 0 and out[2] == -750 and out[3] == -101 and out[0] > out[1] > 0
```

```python
# tests/test_missions.py
from kumoniji.wallet import missions

S0 = {"five": 0, "triple": 0, "oddeven": 0, "fullhouse": 0, "today": 0}


def test_day_is_korean_midnight():
    assert missions.day_of(1764514799) == "2025-11-30"   # 2025-11-30 23:59:59 KST
    assert missions.day_of(1764514800) == "2025-12-01"   # 2025-12-01 00:00:00 KST(UTC로는 11-30 15:00)


def test_missions_need_their_counts():
    c = {}
    for _ in range(4):
        c = missions.add_game(c, S0, rank=2, left=5, points=-3)
    assert missions.done(c) == []
    c = missions.add_game(c, S0 | {"five": 3, "triple": 2, "today": 1, "oddeven": 1, "fullhouse": 1}, rank=1, left=0, points=31)
    assert missions.done(c) == ["games5", "low3", "five3", "triple2", "today", "score30", "oddeven", "fullhouse"]
    c = missions.add_game(c, S0, rank=1, left=0, points=1)
    assert "wins2" in missions.done(c)
```

- [ ] **Step 2: 실패 확인** — `pytest -q tests/test_wallet_money.py tests/test_missions.py` → `ModuleNotFoundError: kumoniji.wallet`

- [ ] **Step 3: 구현**

```python
# wallet/money.py
"""화폐 숫자와 순수 계산(DB 없음). 숫자를 바꿀 땐 이 파일만 — 근거는 계획 D 'Claude가 정한 기본값'."""

POINT = 50            # 1점 = 판돈 50(11-24 사용자)
MIN_STAKE = 500       # 자동 매칭 입장 최소 판돈
HEART_MAX, HEART_EVERY = 10, 600
ATTEND, ATTEND_7TH, ATTEND_7TH_GEMS = 200, 500, 10
MISSION, MISSION_BONUS, MISSION_NEED = 100, 300, 5
SHOP = {"hearts5": (10, {"hearts": 5}), "coins1000": (10, {"coins": 1000})}  # 상품: (보석 값, 얻는 것)


def regen(hearts: int, since: float, now: float) -> tuple[int, float]:
    """10분에 1개, 10개까지. 10 이상(산 하트 포함)이면 충전 없이 기준 시각을 지금으로."""
    if hearts >= HEART_MAX:
        return hearts, now
    got = int((now - since) // HEART_EVERY)
    if hearts + got >= HEART_MAX:
        return HEART_MAX, now
    return hearts + got, since + got * HEART_EVERY


def stake(points: list[int], balances: list[int]) -> list[int]:
    """판돈 증감. 진 사람은 점수×50을 내되 잔고까지만, 이긴 사람은 실제로 걷힌 돈을 + 점수 비율로 나눈다(합 0)."""
    paid = [min(-p * POINT, b) if p < 0 else 0 for p, b in zip(points, balances)]
    pot = sum(paid)
    plus = [max(p, 0) for p in points]
    total = sum(plus) or 1
    got = [pot * p // total for p in plus]
    if pot and any(plus):
        got[max(range(len(plus)), key=lambda i: plus[i])] += pot - sum(got)  # 나머지는 가장 많이 받는 사람에게
    return [g - p for g, p in zip(got, paid)]
```

```python
# wallet/missions.py
"""일일 미션(11-24 사용자 확정 10개, 5개 완료). 하루는 한국 시간 자정 기준. 순수 함수."""
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
MISSIONS = ["games5", "games10", "wins2", "low3", "five3", "triple2", "today", "score30", "oddeven", "fullhouse"]
NEED = {
    "games5": ("games", 5), "games10": ("games", 10), "wins2": ("wins", 2), "low3": ("low3", 1),
    "five3": ("five", 3), "triple2": ("triple", 2), "today": ("today", 1), "score30": ("score", 30),
    "oddeven": ("oddeven", 1), "fullhouse": ("fullhouse", 1),
}


def day_of(ts: float) -> str:
    return datetime.fromtimestamp(ts, KST).date().isoformat()


def add_game(c: dict, seat_stats: dict, rank: int, left: int, points: int) -> dict:
    """그날 누적(c)에 한 판을 더한 새 dict."""
    out = dict(c)
    add = {**seat_stats, "games": 1, "wins": int(rank == 1), "low3": int(left <= 3), "score": max(points, 0)}
    for k, v in add.items():
        out[k] = out.get(k, 0) + v
    return out


def done(c: dict) -> list[str]:
    return [m for m in MISSIONS if c.get(NEED[m][0], 0) >= NEED[m][1]]
```

- [ ] **Step 4: 통과 확인** — 같은 명령 → PASS

- [ ] **Step 5: 커밋** — `git commit -m "feat: 쿠모니지 화폐 순수 계산"`

---

### Task 3: DB — 잔고·원장·하루 기록, 판 끝 기록

**Files:**
- Create: `server/kumoniji/accounts/migrations/003_wallet.sql`, `server/kumoniji/wallet/store.py`
- Test: `server/tests/accounts/test_wallet.py`(실제 Postgres — `database` 픽스처, `make_account` 도우미)

**Interfaces:**
- Consumes: Task 2 전부, `accounts.db.tx()`
- Produces:
  - `store.snapshot(c, account_id, now) -> dict` — `{"coins", "gems", "hearts", "next_heart"(초|None), "attend": {"day", "streak", "claimed"}, "missions": {"done": [...], "counts": {...}, "bonus": bool}}`
  - `store.use_heart(c, account_id, now) -> bool` — 있으면 1개 쓰고 True
  - `store.finish_game(c, game_ref: str, players: list[dict], now) -> None` — `players[i] = {"account": id|None, "stats": dict, "rank": int, "left": int, "points": int}`, `stake: bool`(자동 매칭만 True), `heart: bool`(멀티만 True — 싱글은 시작 때 씀)
  - `store.attend(c, account_id, now) -> dict` — 그날 이미 받았으면 `LookupError("attended")`
  - `store.buy(c, account_id, item, now) -> dict` — 보석 부족 `LookupError("gems")`, 없는 상품 `KeyError`

- [ ] **Step 1: 마이그레이션**

```sql
-- 003_wallet.sql — 화폐(계획 D). 잔고는 wallets, 모든 증감은 ledger(같은 kind+ref는 한 번만).
CREATE TABLE wallets (
  account_id    bigint PRIMARY KEY REFERENCES accounts ON DELETE CASCADE,
  coins         bigint  NOT NULL DEFAULT 0  CHECK (coins >= 0),
  gems          integer NOT NULL DEFAULT 0  CHECK (gems >= 0),
  hearts        integer NOT NULL DEFAULT 10 CHECK (hearts >= 0),
  hearts_at     timestamptz NOT NULL DEFAULT now(),
  attend_day    date,
  attend_streak integer NOT NULL DEFAULT 0
);
CREATE TABLE ledger (
  id         bigserial PRIMARY KEY,
  account_id bigint NOT NULL REFERENCES accounts ON DELETE CASCADE,
  kind       text NOT NULL,          -- stake·heart·attend·mission·bonus·buy
  ref        text NOT NULL,          -- 판 id, 날짜+미션 id 등
  coins      bigint  NOT NULL DEFAULT 0,
  gems       integer NOT NULL DEFAULT 0,
  hearts     integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (account_id, kind, ref)
);
CREATE TABLE daily (
  account_id bigint NOT NULL REFERENCES accounts ON DELETE CASCADE,
  day        date NOT NULL,
  counts     jsonb NOT NULL DEFAULT '{}',
  PRIMARY KEY (account_id, day)
);
```

- [ ] **Step 2: 실패하는 테스트**

```python
# tests/accounts/test_wallet.py
import time

import pytest

from kumoniji.accounts import db
from kumoniji.wallet import money, store

from .helpers import make_account

S0 = {"five": 0, "triple": 0, "oddeven": 0, "fullhouse": 0, "today": 0}


def P(a, rank, points, left=3, stats=S0):
    return {"account": a, "stats": stats, "rank": rank, "left": left, "points": points}


def test_new_wallet_has_ten_hearts_and_nothing_else(database):
    a = make_account()
    with db.tx() as c:
        w = store.snapshot(c, a, time.time())
    assert (w["coins"], w["gems"], w["hearts"]) == (0, 0, 10)


def test_auto_match_game_moves_coins_once_even_if_recorded_twice(database):
    ids = [make_account(email=f"w{i}@x.com", nickname=f"w{i}") for i in range(4)]
    with db.tx() as c:
        for a in ids:
            c.execute("INSERT INTO wallets (account_id, coins) VALUES (%s, 10000)", (a,))
    players = [P(ids[0], 1, 60, left=0), P(ids[1], 2, -10), P(ids[2], 3, -20), P(ids[3], 4, -30)]
    for _ in range(2):  # 같은 판을 두 번 기록해도(재시도) 한 번만
        with db.tx() as c:
            store.finish_game(c, "t1", players, time.time(), stake=True, heart=True)
    with db.tx() as c:
        got = [store.snapshot(c, a, time.time()) for a in ids]
    assert [w["coins"] for w in got] == [13000, 9500, 9000, 8500]
    assert [w["hearts"] for w in got] == [9, 9, 9, 9]
    assert got[0]["missions"]["counts"]["games"] == 1


def test_friend_room_and_single_give_points_for_missions_but_no_coins(database):
    a = make_account()
    with db.tx() as c:
        store.finish_game(c, "s1", [P(a, 1, 40, left=0), P(None, 2, -40), P(None, 3, 0), P(None, 4, 0)], time.time(), stake=False, heart=False)
        w = store.snapshot(c, a, time.time())
    assert w["coins"] == money.MISSION * 2  # low3, score30 달성 → 미션 보상만
    assert set(w["missions"]["done"]) == {"low3", "score30"}


def test_five_missions_pay_bonus_once(database):
    a = make_account()
    st = S0 | {"five": 3, "triple": 2, "today": 1, "oddeven": 1, "fullhouse": 1}
    with db.tx() as c:
        store.finish_game(c, "g1", [P(a, 1, 31, left=0, stats=st), P(None, 2, 0), P(None, 3, 0), P(None, 4, 0)], time.time(), stake=False, heart=False)
        store.finish_game(c, "g2", [P(a, 1, 31, left=0, stats=st), P(None, 2, 0), P(None, 3, 0), P(None, 4, 0)], time.time(), stake=False, heart=False)
        w = store.snapshot(c, a, time.time())
    assert w["missions"]["bonus"] is True
    assert w["coins"] == money.MISSION * len(w["missions"]["done"]) + money.MISSION_BONUS


def test_attend_once_a_day_and_seventh_day_gives_more(database):
    a = make_account()
    day = 86400
    t0 = 1764514800  # 2025-12-01 00:00 KST
    with db.tx() as c:
        for i in range(7):
            store.attend(c, a, t0 + i * day)
        with pytest.raises(LookupError):
            store.attend(c, a, t0 + 6 * day + 60)
        w = store.snapshot(c, a, t0 + 6 * day + 60)
    assert w["coins"] == money.ATTEND * 6 + money.ATTEND_7TH and w["gems"] == money.ATTEND_7TH_GEMS


def test_buy_with_gems_and_hearts_can_exceed_ten(database):
    a = make_account()
    with db.tx() as c:
        c.execute("INSERT INTO wallets (account_id, gems) VALUES (%s, 15)", (a,))
        store.buy(c, a, "hearts5", time.time())
        with pytest.raises(LookupError):
            store.buy(c, a, "hearts5", time.time())  # 보석 5 남음
        w = store.snapshot(c, a, time.time())
    assert (w["gems"], w["hearts"]) == (5, 15)
```

- [ ] **Step 3: 실패 확인** — `pytest -q tests/accounts/test_wallet.py` → `ModuleNotFoundError: kumoniji.wallet.store`

- [ ] **Step 4: 구현**

```python
# wallet/store.py
"""화폐 DB. 잔고 행은 FOR UPDATE로 잠그고, 증감은 원장(ledger)에 먼저 넣어 같은 kind+ref가 두 번 들어가지 않게 한다."""
import json
from datetime import datetime, timezone

from . import missions, money


def _ts(dt) -> float:
    return dt.timestamp()


def _wallet(c, a: int, now: float) -> dict:
    c.execute("INSERT INTO wallets (account_id) VALUES (%s) ON CONFLICT DO NOTHING", (a,))
    w = c.execute("SELECT * FROM wallets WHERE account_id = %s FOR UPDATE", (a,)).fetchone()
    hearts, since = money.regen(w["hearts"], _ts(w["hearts_at"]), now)
    if (hearts, since) != (w["hearts"], _ts(w["hearts_at"])):
        c.execute(
            "UPDATE wallets SET hearts = %s, hearts_at = %s WHERE account_id = %s",
            (hearts, datetime.fromtimestamp(since, timezone.utc), a),
        )
        w = {**w, "hearts": hearts, "hearts_at": datetime.fromtimestamp(since, timezone.utc)}
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


def snapshot(c, a: int, now: float) -> dict:
    w = _wallet(c, a, now)
    day = missions.day_of(now)
    d = c.execute("SELECT counts FROM daily WHERE account_id = %s AND day = %s", (a, day)).fetchone()
    counts = d["counts"] if d else {}
    done = missions.done(counts)
    nxt = None if w["hearts"] >= money.HEART_MAX else _ts(w["hearts_at"]) + money.HEART_EVERY
    return {
        "coins": w["coins"], "gems": w["gems"], "hearts": w["hearts"], "next_heart": nxt,
        "attend": {"day": day, "streak": w["attend_streak"], "claimed": str(w["attend_day"]) == day},
        "missions": {"all": missions.MISSIONS, "done": done, "counts": counts, "bonus": len(done) >= money.MISSION_NEED},
    }


def use_heart(c, a: int, now: float) -> bool:
    w = _wallet(c, a, now)
    if w["hearts"] < 1:
        return False
    hearts_at = "hearts_at" if w["hearts"] < money.HEART_MAX else "now()"  # 10에서 하나 쓰면 충전은 지금부터
    c.execute(f"UPDATE wallets SET hearts = hearts - 1, hearts_at = {hearts_at} WHERE account_id = %s", (a,))
    c.execute("INSERT INTO ledger (account_id, kind, ref, hearts) VALUES (%s, 'heart', %s, -1)", (a, f"use:{now}"))
    return True


def finish_game(c, ref: str, players: list[dict], now: float, *, stake: bool, heart: bool) -> None:
    """판 끝: (자동 매칭이면) 판돈, (멀티면) 하트, 그날 미션 누적·보상. 같은 ref는 한 번만(원장 'game' 표식)."""
    people = [p for p in players if p["account"] is not None]
    for p in sorted(people, key=lambda p: p["account"]):  # 잠그는 순서를 고정해 교착 방지
        _wallet(c, p["account"], now)
    if not _apply(c, people[0]["account"], "game", ref):  # 이미 기록한 판(재시도) — 아무것도 안 한다
        return
    for p in people[1:]:
        _apply(c, p["account"], "game", ref)
    if stake:
        bal = [c.execute("SELECT coins FROM wallets WHERE account_id = %s", (p["account"],)).fetchone()["coins"] for p in players]
        for p, delta in zip(players, money.stake([p["points"] for p in players], bal)):
            _apply(c, p["account"], "stake", ref, coins=delta)
    day = missions.day_of(now)
    for p in people:
        a = p["account"]
        if heart:
            hearts = c.execute("SELECT hearts FROM wallets WHERE account_id = %s", (a,)).fetchone()["hearts"]
            _apply(c, a, "heart", ref, hearts=-min(1, hearts))
        d = c.execute("SELECT counts FROM daily WHERE account_id = %s AND day = %s", (a, day)).fetchone()
        before = missions.done(d["counts"] if d else {})
        counts = missions.add_game(d["counts"] if d else {}, p["stats"], p["rank"], p["left"], p["points"])
        c.execute(
            """INSERT INTO daily (account_id, day, counts) VALUES (%s, %s, %s)
               ON CONFLICT (account_id, day) DO UPDATE SET counts = EXCLUDED.counts""",
            (a, day, json.dumps(counts)),
        )
        after = missions.done(counts)
        for m in after:
            if m not in before:
                _apply(c, a, "mission", f"{day}:{m}", coins=money.MISSION)
        if len(after) >= money.MISSION_NEED:
            _apply(c, a, "bonus", day, coins=money.MISSION_BONUS)


def attend(c, a: int, now: float) -> dict:
    w = _wallet(c, a, now)
    day = missions.day_of(now)
    if str(w["attend_day"]) == day:
        raise LookupError("attended")
    yesterday = missions.day_of(now - 86400)
    streak = w["attend_streak"] + 1 if str(w["attend_day"]) == yesterday else 1
    seventh = streak % 7 == 0
    c.execute("UPDATE wallets SET attend_day = %s, attend_streak = %s WHERE account_id = %s", (day, streak, a))
    _apply(c, a, "attend", day, coins=money.ATTEND_7TH if seventh else money.ATTEND, gems=money.ATTEND_7TH_GEMS if seventh else 0)
    return snapshot(c, a, now)


def buy(c, a: int, item: str, now: float) -> dict:
    price, gives = money.SHOP[item]  # 없는 상품 → KeyError
    w = _wallet(c, a, now)
    if w["gems"] < price:
        raise LookupError("gems")
    _apply(c, a, "buy", f"{item}:{now}", gems=-price, coins=gives.get("coins", 0), hearts=gives.get("hearts", 0))
    return snapshot(c, a, now)
```

- [ ] **Step 5: 통과 확인** — `pytest -q tests/accounts/test_wallet.py` → PASS. 이어서 서버 전체(`pytest -q`)로 마이그레이션이 기존 테스트를 깨지 않는지 확인.

- [ ] **Step 6: 커밋** — `git commit -m "feat: 쿠모니지 화폐 DB·원장"`

---

### Task 4: API 연결 — `/api/wallet`, 싱글 하트·판 끝 기록

**Files:**
- Create: `server/kumoniji/wallet/web.py`
- Modify: `server/kumoniji/api.py` (`new_game`, `move`, 라우터 등록, `Room`에 `recorded: bool`)
- Test: `server/tests/accounts/test_wallet.py`에 HTTP 테스트 추가

**Interfaces:**
- Consumes: Task 3 `store.*`, `accounts.web.player`
- Produces: `GET /api/wallet` → `snapshot`, `POST /api/wallet/attend` → `snapshot`(이미 받았으면 409 `{"code":"attended"}`), `POST /api/wallet/buy {"item"}` → `snapshot`(보석 부족 409 `{"code":"gems"}`, 없는 상품 422). `POST /api/games`는 하트가 없으면 402 `{"code":"no_heart"}`. 판이 끝난 `view` 응답에 `"wallet": snapshot` 추가.

- [ ] **Step 1: 실패하는 테스트**

```python
# tests/accounts/test_wallet.py 에 추가
from .helpers import browser, login, signed_up


def test_single_game_uses_a_heart_and_refuses_at_zero(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    assert c.post("/api/games").status_code == 200
    assert c.get("/api/wallet").json()["hearts"] == 9
    with db.tx() as x:
        x.execute("UPDATE wallets SET hearts = 0, hearts_at = now()")
    r = c.post("/api/games")
    assert r.status_code == 402 and r.json()["detail"]["code"] == "no_heart"


def test_attend_and_buy_over_http(outbox, fast_hash):
    c = browser()
    signed_up(c, outbox)
    login(c)
    assert c.post("/api/wallet/attend").json()["coins"] == money.ATTEND
    assert c.post("/api/wallet/attend").status_code == 409
    assert c.post("/api/wallet/buy", json={"item": "hearts5"}).json()["detail"]["code"] == "gems"
    assert c.post("/api/wallet/buy", json={"item": "nope"}).status_code == 422
```

- [ ] **Step 2: 실패 확인** — `pytest -q tests/accounts/test_wallet.py -k "http or heart"` → 404

- [ ] **Step 3: 구현**

```python
# wallet/web.py
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..accounts import db
from ..accounts.web import check_csrf_dep, player
from . import store

router = APIRouter(prefix="/api/wallet")


class Buy(BaseModel):
    item: Literal["hearts5", "coins1000"]


@router.get("")
def wallet(me: dict = Depends(player)):
    with db.tx() as c:
        return store.snapshot(c, me["account_id"], time.time())


@router.post("/attend")
def attend(me: dict = Depends(player)):
    try:
        with db.tx() as c:
            return store.attend(c, me["account_id"], time.time())
    except LookupError:
        raise HTTPException(409, {"code": "attended"}) from None


@router.post("/buy")
def buy(body: Buy, me: dict = Depends(player)):
    try:
        with db.tx() as c:
            return store.buy(c, me["account_id"], body.item, time.time())
    except LookupError:
        raise HTTPException(409, {"code": "gems"}) from None
```
(POST의 CSRF는 기존 `player`/미들웨어가 하는 방식을 그대로 따른다 — 구현 전 `accounts/web.py`에서 다른 POST 라우트가 CSRF를 어떻게 거는지 확인해 같은 방식으로. 위 import의 `check_csrf_dep`은 실제 이름으로 바꾼다.)

```python
# api.py — new_game 맨 앞
    with db.tx() as c:
        if not store.use_heart(c, me["account_id"], time.time()):
            raise HTTPException(402, {"code": "no_heart"})

# api.py — 판 끝 기록(새 함수). new_game·move에서 run_bots 뒤에 부른다.
def _finish(room: Room, gid: str, out: dict) -> dict:
    g = room.game
    if g.winner is None or room.recorded:
        return out
    pts = g.settlement()
    rank = sorted(range(4), key=lambda i: (i != g.winner, -pts[i]))
    players = [
        {"account": room.account_id if i == HUMAN else None, "stats": g.stats[i], "rank": rank.index(i) + 1,
         "left": len(g.hands[i]), "points": pts[i]}
        for i in range(4)
    ]
    try:
        with db.tx() as c:
            store.finish_game(c, f"single:{gid}", players, time.time(), stake=False, heart=False)
            out["wallet"] = store.snapshot(c, room.account_id, time.time())
        room.recorded = True
    except Exception:
        log.exception("판 끝 기록 실패")  # 결과 화면은 그대로 보여 준다. 다음 GET에서 다시 시도
    return out
```
(`move`·`new_game`·`get_game`의 `return view(...)`를 `return _finish(room, gid, view(...))`로. `app.include_router(wallet_web.router)`.)

- [ ] **Step 4: 통과 확인** — `pytest -q` 전체 PASS(기존 싱글 테스트가 하트 10개 안에서 판을 여는지 확인 — 11판 이상 여는 테스트가 있으면 그 테스트에서만 하트를 채운다)

- [ ] **Step 5: 커밋** — `git commit -m "feat: 쿠모니지 지갑 API·싱글 하트"`

---

### Task 5: 멀티 연결 — 입장 조건과 판 끝 기록

**Files:**
- Modify: `server/kumoniji/accounts/web.py` (`socket_session`에 `"wallet": store.snapshot(...)`), `server/kumoniji/multi/ws.py`, `server/kumoniji/multi/table.py` (`MultiTable.kind: str` = `"auto"|"room"`, `recorded: bool`)
- Modify: `server/kumoniji/multi/lobby.py` (`_start(players, now, kind)`)
- Test: `server/tests/accounts/test_ws.py`

**Interfaces:**
- Consumes: Task 3 `store.finish_game`·`store.snapshot`
- Produces: `queue` 거절 오류 `{"t":"error","code":"no_heart"}`·`{"t":"error","code":"low_coins"}`, 친구방 시작은 하트만 본다. 판이 끝나면 각 자리에 `{"t":"wallet", ...snapshot}`.

- [ ] **Step 1: 실패하는 테스트**

```python
# tests/accounts/test_ws.py 에 추가
def test_queue_needs_min_coins_and_a_heart(server, outbox):
    w = connect(server, account(outbox, 1), 1)
    w.send_json({"t": "queue"})
    assert until(w, "error") == {"t": "error", "code": "low_coins"}  # 새 계정은 판돈 0


def test_auto_match_game_end_pays_coins_and_sends_wallet(server, outbox, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(multi_ws, "clock", lambda: now[0])
    monkeypatch.setattr(multi_ws, "RATE", 1000)
    tokens = [account(outbox, n) for n in range(4)]
    with db.tx() as c:
        c.execute("UPDATE wallets SET coins = 100000")  # account()가 지갑을 만든 뒤(connect가 snapshot)라면 connect 뒤로
    ws = [connect(server, t, n) for n, t in enumerate(tokens)]
    for w in ws:
        w.send_json({"t": "queue"})
    states = [until(w, "state") for w in ws]
    multi_ws.LOBBY.tables[states[0]["id"]].game.hands = [[("솜", 1)], [("솜", 2)], [("솜", 3)], [("산", 13)]]
    # … 차례인 자리가 마지막 패를 내 판을 끝낸 뒤:
    got = [until(w, "wallet") for w in ws]
    assert sum(g["coins"] for g in got) == 400000 and all(g["hearts"] == 9 for g in got)
```
(두 번째 테스트의 판 끝내기는 `test_ws.py`의 기존 "4명 전체 판" 테스트가 판을 끝내는 방법을 그대로 쓴다 — 구현 전에 그 테스트를 읽고 맞춘다. 손패를 직접 바꾸면 `settle`이 깨지는 것은 11-24 작업 일지에 기록된 함정이라 피한다.)

- [ ] **Step 2: 실패 확인** — `pytest -q tests/accounts/test_ws.py -k "min_coins or pays_coins"` → FAIL

- [ ] **Step 3: 구현**
  - `socket_session`: 반환 dict에 `"wallet": store.snapshot(c, s["account_id"], time.time())`(같은 트랜잭션).
  - `ws.py`: 연결별 `SESS[ws]["wallet"]`. `_handle`의 `queue`에서 `w = SESS[...]["wallet"]`로 `w["hearts"] < 1` → `LobbyError("no_heart")`, `w["coins"] < money.MIN_STAKE` → `LobbyError("low_coins")`. `room.start`는 방 사람 모두 `hearts ≥ 1`인지(아니면 `no_heart`).
    - ponytail: 스냅숏은 연결 때와 판 끝 때만 새로 읽는다 — 그사이 싱글로 하트를 다 쓰면 멀티 판 끝에 0에서 멈춘다(`finish_game`의 `min(1, hearts)`).
  - `lobby._start(players, now, kind)`: `enqueue`→`"auto"`, `start_room`→`"room"`. `MultiTable.kind`에 저장.
  - 판 끝: `push()`가 `t.game.winner is not None and not t.recorded`를 보면 `t.recorded = True` 후 `asyncio.get_running_loop().create_task(_record(t))`.

```python
async def _record(t: MultiTable) -> None:
    g = t.game
    pts = g.settlement()
    rank = sorted(range(4), key=lambda i: (i != g.winner, -pts[i]))
    players = [
        {"account": a, "stats": g.stats[i], "rank": rank.index(i) + 1, "left": len(g.hands[i]), "points": pts[i]}
        for i, a in enumerate(t.accounts)
    ]

    def write():
        with db.tx() as c:
            store.finish_game(c, f"multi:{t.id}", players, time.time(), stake=t.kind == "auto", heart=True)
            return [store.snapshot(c, a, time.time()) for a in t.accounts]

    try:
        snaps = await _db("recheck", write)
    except Exception:
        log.exception("멀티 판 끝 기록 실패")
        return
    for a, w in zip(t.accounts, snaps):
        if (ws := CONNS.get(a)) is not None and ws in SESS:
            SESS[ws]["wallet"] = w
        send(a, {"t": "wallet", **w})
```

- [ ] **Step 4: 통과 확인** — `pytest -q` 전체 PASS

- [ ] **Step 5: 커밋** — `git commit -m "feat: 쿠모니지 멀티 판돈 정산·입장 조건"`

---

### Task 6: 앱 — 잔고 막대·출석·미션·상점

**Files:**
- Create: `app/lib/wallet.dart`
- Modify: `app/lib/home_screen.dart`(위에 잔고 막대, 출석·미션·상점 버튼), `app/lib/table_screen.dart`(새 판 402 → 하트 안내, 판 끝 응답의 `wallet`로 막대 갱신), `app/lib/l10n/app_{ko,en,ja,zh}.arb`
- Test: `app/test/wallet_test.dart`

**Interfaces:**
- Consumes: Task 4 API
- Produces: `Wallet.current: ValueNotifier<WalletState?>`, `Wallet.refresh()`, `Wallet.attend()`, `Wallet.buy(String item)`, 위젯 `WalletBar`, 화면 `MissionsScreen`, `ShopScreen`

- [ ] **Step 1: 실패하는 테스트**

```dart
// test/wallet_test.dart
testWidgets('잔고 막대가 판돈·하트·보석을 보여 주고 출석을 누르면 늘어난다', (t) async {
  var coins = 0;
  Auth.client = AuthClient(MockClient((r) async {
    if (r.url.path == '/api/wallet/attend') coins += 200;
    return http.Response(jsonEncode({
      'coins': coins, 'gems': 0, 'hearts': 10, 'next_heart': null,
      'attend': {'day': '2026-11-24', 'streak': 1, 'claimed': coins > 0},
      'missions': {'all': ['games5'], 'done': [], 'counts': {}, 'bonus': false},
    }), 200);
  }));
  await t.pumpWidget(wrap(const WalletBar()));   // wrap: 기존 테스트의 MaterialApp+l10n 감싸개
  await Wallet.refresh();
  await t.pumpAndSettle();
  expect(find.text('0'), findsOneWidget);
  await Wallet.attend();
  await t.pumpAndSettle();
  expect(find.text('200'), findsOneWidget);
});
```

- [ ] **Step 2: 실패 확인** — `flutter test test/wallet_test.dart` → 컴파일 오류(`Wallet` 없음)

- [ ] **Step 3: 구현** — `wallet.dart`

```dart
import 'dart:convert';

import 'package:flutter/material.dart';

import 'api.dart';
import 'auth.dart';
import 'l10n/app_localizations.dart';

class WalletState {
  WalletState(this.j);
  final Map<String, dynamic> j;
  int get coins => j['coins'] as int;
  int get gems => j['gems'] as int;
  int get hearts => j['hearts'] as int;
  bool get attended => (j['attend'] as Map)['claimed'] as bool;
  List<String> get done => List<String>.from((j['missions'] as Map)['done'] as List);
  Map<String, dynamic> get counts => Map<String, dynamic>.from((j['missions'] as Map)['counts'] as Map);
}

class Wallet {
  static final current = ValueNotifier<WalletState?>(null);
  static void set(Map<String, dynamic> j) => current.value = WalletState(j);

  static Future<void> _call(String method, String path, [Object? body]) async {
    final uri = Uri.parse('${Api.base}$path');
    final r = method == 'GET'
        ? await Auth.client.get(uri)
        : await Auth.client.post(uri, headers: {'content-type': 'application/json'}, body: jsonEncode(body ?? {}));
    if (r.statusCode == 200) set(jsonDecode(r.body) as Map<String, dynamic>);
  }

  static Future<void> refresh() => _call('GET', '/api/wallet');
  static Future<void> attend() => _call('POST', '/api/wallet/attend');
  static Future<void> buy(String item) => _call('POST', '/api/wallet/buy', {'item': item});
}

class WalletBar extends StatelessWidget {
  const WalletBar({super.key});
  @override
  Widget build(BuildContext context) => ValueListenableBuilder(
    valueListenable: Wallet.current,
    builder: (_, w, _) => w == null
        ? const SizedBox.shrink()
        : Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            const Icon(Icons.toll, size: 18), Text('${w.coins}'), const SizedBox(width: 12),
            const Icon(Icons.favorite, size: 18, color: Colors.pink), Text('${w.hearts}'), const SizedBox(width: 12),
            const Icon(Icons.diamond, size: 18), Text('${w.gems}'),
          ]),
  );
}
```
  - `MissionsScreen`: 10개 미션을 `t.mission_<id>` 문구 + 진행 수(`counts`)/목표로 보여 주고, 완료면 체크. 위에 "5개 완료 시 +300"과 출석 버튼(받았으면 비활성).
  - `ShopScreen`: 상품 두 개(보석 10 → 하트 5, 보석 10 → 판돈 1,000), 보석 부족이면 버튼 비활성.
  - 홈: 로그인 후 `Wallet.refresh()`, 위에 `WalletBar`, 버튼 "미션·출석"·"상점".
  - 새 판 402 `no_heart` → "하트가 없어요. 10분마다 1개씩 차요" 안내.
  - 멀티 소켓 오류(11-25 B안·리뷰 뒤 서버 기준, **11-26: 앱에 멀티 화면이 아직 없어 멀티 ③ 앱에서 붙인다**): `no_heart`·`low_coins`(판이 잡힐 때 모자라면 그 사람만 받고 로비로), `settling`(앞 판 정산 중 — 잠시 뒤 다시), `busy`(입장 미리 보기 시간 초과), `room_changed`(시작 누른 사이 방 구성이 바뀜 — 다시 누르기). 판이 잡혀 하트를 쓰는 동안은 처지 알림이 없고 곧 판 상태나 위 오류가 온다.
  - arb 4개에 키 추가: `coins`·`hearts`·`gems`·`attend`·`attended`·`missions`·`missionsDone`(5개 완료 보너스)·`shop`·`noHeart`·`lowCoins`·`mission_games5`…`mission_fullhouse`(10개).

- [ ] **Step 4: 통과 확인** — `flutter analyze` 0, `flutter test` 전체 PASS. 홈·미션·상점 화면을 웹 빌드해 캡처(메모: 윈도우 크롬 `--headless=new --screenshot`, 로그인 필요 화면은 가짜 응답 임시 진입점 → 지움).

- [ ] **Step 5: 커밋** — `git commit -m "feat: 쿠모니지 지갑 화면"`(앱은 별도 PR)

---

### Task 7: 문서·배포

- ADR-0024 "쿠모니지 화폐 — 1점당 50, 자동 매칭만, 큰 지급 없음"(이 계획 PR에 함께).
- `_docs/STATE.md`·`WORK_LOG_KUMONIJI.md`, `kumoniji/CLAUDE.md`에 "숫자는 `wallet/money.py`".
- 배포: 마이그레이션 003은 파드가 뜰 때 자동 적용(`accounts/db.py migrate`). **배포 전 DB 덤프를 권한다**(사용자 작업, 쿠모니지 DB 컨테이너). 새 환경 변수 없음.
- 탈퇴: 지갑·원장·하루 기록은 `_purge`가 함께 지운다(11-25 리뷰로 바꿈, 계정 행은 남기므로 CASCADE만으로는 안 지워짐). 판 중 탈퇴자가 있으면 그 판 판돈은 없던 일(ADR-0024).

## 이 계획 밖(나중)
- 광고 보상(1회 100·하루 5회): 앱에 광고 SDK를 붙일 때. 웹은 광고 없음.
- 보석 결제: 게임위 문의 뒤(SPEC).
- 멀티 앱 화면(계획 C ③)에서 결과에 판돈 증감 표시 — `{"t":"wallet"}`을 받아 쓰면 된다.
- 짜고 지기 탐지(기획 E6): 판돈이 자동 매칭에만 있고 같은 IP·기기를 한 판에 넣지 않으니 1차는 막힌다. 반복 상대 탐지는 사람이 늘면.
