"""봇(제안 v4 시뮬레이션의 smart/aim 그대로).
smart: 따라갈 때 이기는 가장 약한 패, 선일 때 가장 약한 타일이 든 가장 큰 조합
aim  : 보너스가 붙는 패가 있으면 그중 가장 약한 것, 없으면 smart"""

from itertools import combinations, product

from .rules import (
    KINDS5,
    ODD_EVEN,
    SHAPES,
    STRAIGHTS,
    beats,
    classify,
    special_steps,
    value,
)


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


def choose(kind, hand, table, rng):
    legal = [p for p in plays(hand) if beats(table, p)]
    if not legal:
        return None
    if kind == "random":
        if table and rng.random() < 0.3:
            return None
        return rng.choice(legal)
    if table:
        return min(legal, key=strength)
    low = min(hand, key=value)
    return max(
        (p for p in legal if low in p), key=lambda p: (len(p), -max(map(value, p)))
    )


def pick(kind, hand, table, today, rng):
    if kind == "aim":
        legal = [p for p in plays(hand) if beats(table, p)]
        good = [p for p in legal if special_steps(p, today, finish=len(p) == len(hand))]
        if good:
            return min(good, key=strength)
    return choose("smart", hand, table, rng)
