"""봇 세 단계(ADR-0022, 11-24 사용자 결정: 난이도는 "패를 가장 빨리 털고 잃는 점수를 줄이는 정도"로 나눈다).
봇은 Seen(공개 정보 + 자기 손패)만 받는다 — 남의 손패는 자리별로 모른다.
easy  : 이길 수 있는 가장 약한 패(계획 없음), 따라갈 때 30% 패스
normal: 수마다 반반으로 easy 수 또는 털기 계획(plan) 수
hard  : 털기 계획(plan) — 손패를 가장 적은 횟수로 터는 계획을 깨지 않는 가장 약한 패.
        끝판(누가 거의 다 털었거나 남은 패가 적을 때)엔 안 나온 패를 무작위로 여러 번 나눠
        plan끼리 끝까지 쳐 보고 내 정산 점수가 가장 좋은(잃는 점수가 가장 적은) 수"""

import time
from collections import defaultdict
from dataclasses import dataclass
from functools import cache, lru_cache
from itertools import combinations, product

from .game import Game, Tile
from .rules import (
    DECK,
    KINDS5,
    ODD_EVEN,
    SHAPES,
    STRAIGHTS,
    beats,
    classify,
    value,
)

LEVELS = ("easy", "normal", "hard")
SAMPLES = 24  # hard 끝판 한 수에 나눠 보는 횟수
BUDGET = 0.4  # 끝판 계산 시간 상한(초) — 넘으면 그때까지 나눠 본 것으로 정한다(최소 4번). 기준: 봇 한 수 0.5초 안
ENDGAME = 36  # 남은 패가 모두 합쳐 이 장수 이하면 hard가 끝판 계산을 한다
MIX = 0.5  # normal이 털기 계획을 따르는 비율(나머지는 easy 수)


def plays(hand):
    """손패로 낼 수 있는 모든 조합(구성적으로 생성)."""
    out = [[t] for t in hand]
    by_num = {}
    for t in hand:
        by_num.setdefault(t[1], []).append(t)
    for ts in by_num.values():
        out += [list(c) for c in combinations(ts, 2)] + [
            list(c) for c in combinations(ts, 3)
        ]
    five = set()
    for seq in STRAIGHTS + ODD_EVEN:
        if all(n in by_num for n in seq):
            five |= {frozenset(p) for p in product(*(by_num[n] for n in seq))}
    for s in SHAPES:
        same = [t for t in hand if t[0] == s]
        five |= {frozenset(c) for c in combinations(same, 5)}
    trips = [c for ts in by_num.values() for c in combinations(ts, 3)]
    pairs = [c for ts in by_num.values() for c in combinations(ts, 2)]
    five |= {frozenset(a + b) for a in trips for b in pairs if a[0][1] != b[0][1]}
    for ts in by_num.values():
        if len(ts) == 4:
            five |= {frozenset(ts + [k]) for k in hand if k not in ts}
    out += [sorted(f, key=value) for f in five if classify(list(f))]
    return sorted(
        out, key=lambda p: (len(p), [value(t) for t in p])
    )  # 해시 순서와 무관하게


def strength(p):
    c = classify(p)
    return (KINDS5.index(c[0]) if len(p) == 5 else 0, c[1])


def can_beat(table: list, tiles: list) -> bool:
    """tiles로 table을 이기는 조합을 만들 수 있는가."""
    if len(table) == 5:
        return any(len(p) == 5 and beats(table, p) for p in plays(tiles))
    by_num: defaultdict[int, list] = defaultdict(list)
    for t in tiles:
        by_num[t[1]].append(t)
    return any(
        beats(table, list(c))
        for ts in by_num.values()
        for c in combinations(ts, len(table))
    )


@dataclass(frozen=True)
class Seen:
    """한 자리가 아는 것. unseen = 자기 손에 없고 아직 안 나온 타일(남들 손패의 합, 자리 구분 없음)."""

    seat: int
    hand: tuple[Tile, ...]
    unseen: tuple[Tile, ...]
    counts: tuple[int, ...]
    table: tuple[Tile, ...]
    last: int | None
    passes: int
    today: str
    petals: tuple[tuple[str, ...], ...]
    bonus: tuple[int, ...]
    pot: int
    doubles: int


def seen(g: Game, seat: int) -> Seen:
    others = sorted(
        (t for i, h in enumerate(g.hands) if i != seat for t in h), key=value
    )
    return Seen(
        seat=seat,
        hand=tuple(sorted(g.hands[seat], key=value)),
        unseen=tuple(others),
        counts=tuple(len(h) for h in g.hands),
        table=tuple(g.table),
        last=g.last,
        passes=g.passes,
        today=g.today,
        petals=tuple(tuple(p) for p in g.petals),
        bonus=tuple(g.bonus),
        pot=g.pot,
        doubles=g.doubles,
    )


TILES = sorted(DECK, key=value)  # value(t)가 곧 자리 번호(0~51)


def mask(tiles) -> int:
    """타일 묶음을 52비트 정수로(캐시 키를 작게 — 파드 메모리 256Mi)."""
    return sum(1 << value(t) for t in tiles)


def unmask(m: int) -> list[Tile]:
    return [TILES[i] for i in range(52) if m >> i & 1]


def _turns(combos: list[int]):
    """combos(손패의 모든 조합 mask)로 만든 '손패 일부(mask)를 다 털려면 최소 몇 번' 함수.
    손패 일부의 조합은 손패 조합 중 그 안에 든 것이라 조합을 다시 만들지 않는다."""

    @cache
    def go(rest: int) -> int:
        if not rest:
            return 0
        low = rest & -rest  # 가장 약한 타일은 어딘가에 들어가야 한다
        return 1 + min(go(rest ^ c) for c in combos if c & low and c & rest == c)

    return go


def turns(hand: int) -> int:
    """이 손패(mask)를 다 털려면 최소 몇 번 내야 하나(조합으로 나누는 가장 적은 수)."""
    return _turns([mask(p) for p in plays(unmask(hand))])(hand)


def easy(s: Seen, legal, rng):
    # 패스 없이 가장 약한 패만 내면 털기 계획 봇과 거의 같은 세기였다(11-24 하네스: 계획 봇 1등 34.9%) → 30% 패스로 약하게
    if s.table and rng.random() < 0.3:
        return None
    return min(legal, key=strength)


def normal(s: Seen, legal, rng):
    return plan(s, legal, rng) if rng.random() < MIX else easy(s, legal, rng)


def plan(s: Seen, legal, rng):
    m = _plan(mask(s.hand), s.table)
    return list(m) if m else None


@lru_cache(maxsize=1 << 17)
def _plan(hand: int, table: tuple) -> tuple | None:
    """털기 계획은 (손패, 바닥)만 보고 정한다 → 통째로 캐시(hard 끝판 계산이 같은 장면을 수없이 다시 본다)."""
    tiles = unmask(hand)
    every = plays(tiles)
    legal = [p for p in every if beats(list(table), p)]
    if not legal:
        return None
    go = _turns([mask(p) for p in every])
    n = go(hand)
    free = [p for p in legal if go(hand ^ mask(p)) == n - 1]  # 계획을 깨지 않는 패
    if not table:
        low = tiles[0]  # 계획에서 가장 약한 타일이 든 묶음(최적 계획엔 늘 있다)
        return tuple(
            max(
                (p for p in free if low in p),
                key=lambda p: (len(p), [-value(t) for t in p]),
            )
        )
    # 계획을 깨는 패라도 패스보다는 낸다 — 센 패를 아끼거나 패스하는 판이 1등·점수 모두 낮았다(11-21 하네스:
    # 아낌+패스 1등 30%, 이 방식 69%). 남은 13 한 장마다 벌점 ×2라 쥐고 있는 쪽이 손해.
    return tuple(min(free or legal, key=strength))


def hard(s: Seen, legal, rng):
    others = [c for i, c in enumerate(s.counts) if i != s.seat]
    if min(others) <= 3 or len(s.hand) <= 4 or sum(s.counts) <= ENDGAME:
        return endgame(s, legal, rng)
    return plan(s, legal, rng)


def endgame(s: Seen, legal, rng):
    """후보 수마다 안 나온 패를 같은 방식으로 SAMPLES번 나눠 plan끼리 끝까지 친 정산 점수 합이 가장 큰 수."""
    if len(s.hand) in map(len, legal):  # 한 번에 다 털 수 있으면 턴다
        return next(p for p in legal if len(p) == len(s.hand))
    cands = _candidates(s, legal)
    if len(cands) == 1:
        return cands[0]
    deals = [_deal(s, rng) for _ in range(SAMPLES)]
    score = {i: 0 for i in range(len(cands))}
    end = time.monotonic() + BUDGET
    for k, hands in enumerate(deals):
        if k >= 4 and time.monotonic() > end:
            break
        for i, m in enumerate(cands):
            score[i] += _rollout(s, hands, m)
    return cands[max(score, key=lambda i: (score[i], -i))]


def _candidates(s: Seen, legal) -> list:
    """비교할 수: 패스(따라갈 때) + 크기별로 가장 약한 패·가장 센 패 + 계획을 깨지 않는 패."""
    hand = mask(s.hand)
    go = _turns([mask(p) for p in plays(list(s.hand))])
    n = go(hand)
    pick = {tuple(p) for p in legal if go(hand ^ mask(p)) == n - 1}
    for k in {len(p) for p in legal}:
        same = sorted((p for p in legal if len(p) == k), key=strength)
        pick |= {tuple(same[0]), tuple(same[-1])}
    out = sorted((list(p) for p in pick), key=lambda p: (len(p), strength(p)))
    return ([None] if s.table else []) + out


def _deal(s: Seen, rng) -> list[list[Tile]]:
    pool = list(s.unseen)
    rng.shuffle(pool)
    hands, k = [], 0
    for i, c in enumerate(s.counts):
        if i == s.seat:
            hands.append(list(s.hand))
        else:
            hands.append(sorted(pool[k : k + c], key=value))
            k += c
    return hands


def _rollout(s: Seen, hands, first) -> int:
    g = Game(
        hands=[list(h) for h in hands],
        today=s.today,
        turn=s.seat,
        table=list(s.table),
        last=s.last,
        passes=s.passes,
        petals=[list(p) for p in s.petals],
        bonus=list(s.bonus),
        pot=s.pot,
        doubles=s.doubles,
    )
    g.play(s.seat, first)
    while g.winner is None:
        m = _plan(mask(g.hands[g.turn]), tuple(g.table))
        g.play(g.turn, list(m) if m else None)
    return g.settlement()[s.seat]


def pick(level: str, s: Seen, rng):
    """level 봇이 낼 패(None = 패스)."""
    legal = [p for p in plays(list(s.hand)) if beats(list(s.table), p)]
    if not legal:
        return None
    return {"easy": easy, "normal": normal, "hard": hard}[level](s, legal, rng)
