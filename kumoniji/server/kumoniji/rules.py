"""[게임명] 규칙(제안 v4: 오프라인에서도 셈하기 쉬운 정산) 판정 기준 구현 + 하네스 실행기. RULES.md의 [결정] 항목은 초안 기본값.

타일 표기: 모양 한 글자 + 숫자. 벚(벚꽃)·솜(솜사탕)은 분홍, 잎(잎사귀)·산은 초록. 예: "벚3", "산13".
5장 서열은 13장 손패에 나올 확률 순(PROBABILITIES.md).
실행: python3 rules.py          → cases.json 전부 판정
      python3 rules.py --full   → 52장 중 5장 전수 분류(경우의 수 검증)
"""

import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

SHAPES = ["산", "벚", "잎", "솜"]  # 약 → 강
COLOR = {"벚": "분홍", "솜": "분홍", "잎": "초록", "산": "초록"}
NUM_RANK = {n: n - 1 for n in range(1, 14)}  # 1이 가장 약하고 13이 가장 셈 (11-17 v2)
KINDS5 = [
    "스트레이트",
    "풀하우스",
    "홀짝",
    "같은색스트레이트",
    "같은색홀짝",
    "포카드",
    "스트레이트플러시",
    "같은모양홀짝",
]  # 약 → 강
BOMBS = {"포카드", "스트레이트플러시", "같은모양홀짝"}  # 특별 플레이(배수 단계)
STRAIGHTS = [frozenset(range(s, s + 5)) for s in range(1, 10)]  # 1-5 … 9-13, 순환 없음
ODD_EVEN = sorted((frozenset(range(s, s + 10, 2)) for s in range(1, 6)), key=max)
DECK = [(s, n) for s in SHAPES for n in range(1, 14)]
START = ("산", 1)  # 가장 약한 타일 = 선
BONUS, TODAY_MULT = (
    2,
    5,
)  # 보너스 조건당 +2, 오늘의 무늬로만 된 5장마다 ×5 (11-17 사용자 결정)
TILE_POINTS = {
    **{n: 1 for n in range(1, 8)},
    8: 2,
    9: 2,
    10: 2,
    11: 4,
    12: 4,
    13: 5,
}  # 문양 패(구름·무지개·해)는 +1


def parse(text):
    return (text[0], int(text[1:]))


def value(tile):
    return NUM_RANK[tile[1]] * 4 + SHAPES.index(tile[0])


def classify(tiles):
    """조합이면 (종류, 비교 키), 아니면 None. 여러 조합이 동시에 되면 가장 센 것."""
    if not tiles or len(set(tiles)) != len(tiles):
        return None
    nums = [n for _, n in tiles]
    top = max(tiles, key=value)
    if len(tiles) == 1:
        return ("싱글", (value(top),))
    if len(tiles) in (2, 3):
        if len(set(nums)) != 1:
            return None
        return ("페어" if len(tiles) == 2 else "트리플", (value(top),))
    if len(tiles) != 5:
        return None

    groups = Counter(nums).most_common()
    shape = len({s for s, _ in tiles}) == 1
    color = len({COLOR[s] for s, _ in tiles}) == 1
    numset = frozenset(nums)
    seq = (STRAIGHTS.index(numset), value(top)) if numset in STRAIGHTS else None
    odd = (ODD_EVEN.index(numset), value(top)) if numset in ODD_EVEN else None
    if odd and shape:
        return ("같은모양홀짝", odd)
    if seq and shape:
        return ("스트레이트플러시", seq)
    if groups[0][1] == 4:
        return ("포카드", (NUM_RANK[groups[0][0]],))
    if odd and color:
        return ("같은색홀짝", odd)
    if seq and color:
        return ("같은색스트레이트", seq)
    if odd:
        return ("홀짝", odd)
    if [c for _, c in groups] == [3, 2]:
        return ("풀하우스", (NUM_RANK[groups[0][0]],))
    if seq:
        return ("스트레이트", seq)
    return None  # 같은 모양 5장이라도 수열이 아니면 조합 아님(v3: 플러시 삭제)


def beats(prev, new):
    """바닥 조합 prev 위에 new를 낼 수 있는가. prev가 빈 목록이면 선(아무 조합)."""
    b = classify(new)
    if b is None:
        return False
    if not prev:
        return True
    if len(prev) != len(new):
        return False
    a = classify(prev)
    if len(new) == 5:
        return (KINDS5.index(b[0]), b[1]) > (KINDS5.index(a[0]), a[1])
    return b[1] > a[1]


def first_player(hands):
    """산1(가장 약한 타일)을 가진 사람이 선."""
    return next(i for i, h in enumerate(hands) if START in h)


def simulate(hands, moves, today):
    """한 판 진행. moves: 차례대로 낸 타일 목록 또는 "패스". 시계 방향(번호 +1).
    today: 판 시작 때 공개되는 "오늘의 무늬".
    반환 dict: error_at(처음 규칙을 어긴 move 번호), winner, petals(플레이어별 꽃잎 무늬 목록),
    bonus(플레이어별 보너스 점수 — 라운드를 가져간 사람이 그 라운드의 보너스를 모두 받음),
    doubles(오늘의 무늬로만 된 5장 조합이 나온 횟수 → 판 정산 ×5씩)."""
    hands = [list(h) for h in hands]
    turn, table, last, passes = first_player(hands), [], None, 0
    petals, bonus, pot, doubles = [[] for _ in hands], [0] * len(hands), 0, 0

    def result(err):
        winner = last if last is not None and not hands[last] else None
        return dict(
            error_at=err,
            winner=winner,
            petals=petals,
            bonus=bonus,
            doubles=doubles,
            hands=hands,
        )

    for i, move in enumerate(moves):
        if last is not None and not hands[last]:
            return result(i)  # 판이 끝난 뒤의 행동
        if move == "패스":
            if not table:
                return result(i)  # 선은 패스 불가
            passes += 1
            if passes == 3:  # 나머지 3명이 연달아 패스 → 선을 되찾고 꽃잎
                petals[last].append(max(table, key=value)[0])
                bonus[last] += pot + small_today(
                    table, today
                )  # 라운드를 가져간 사람이 그 라운드 보너스를 받는다
                table, passes, pot = [], 0, 0
        else:
            if any(t not in hands[turn] for t in move) or not beats(table, move):
                return result(i)
            for t in move:
                hands[turn].remove(t)
            pot += special_steps(move, today, finish=not hands[turn])
            doubles += len(move) == 5 and all(s == today for s, _ in move)
            table, last, passes = move, turn, 0
            if not hands[turn]:
                bonus[turn] += pot + small_today(
                    move, today
                )  # 마무리한 사람이 마지막 라운드를 가져감
                pot = 0
        turn = (turn + 1) % len(hands)
    return result(None)


def special_steps(move, today, finish):
    """한 번 낸 패로 쌓이는 보너스 점수(각 +2, 11-17). 셋 다 해당하면 +6.
    ① 오늘의 무늬가 3장 이상 든 5장 조합  ② 폭탄(포카드 이상)  ③ 오늘의 무늬 타일이 든 패로 마무리"""
    kind = classify(move)[0]
    return BONUS * (
        (len(move) == 5 and sum(s == today for s, _ in move) >= 3)
        + (kind in BOMBS)
        + (finish and any(s == today for s, _ in move))
    )


def small_today(move, today):
    """오늘의 무늬 타일이 든 싱글·더블·트리플로 라운드를 가져가면 +1(11-17).
    더블·트리플은 같은 숫자라 무늬가 다 같을 수 없으므로 '오늘의 무늬가 한 장 이상 든' 것으로 정의."""
    return int(len(move) <= 3 and any(s == today for s, _ in move))


def settle(hands_left, petals, bonus, doubles):
    """판 끝 정산 → 플레이어별 점수 증감(방 단가 곱하기 전). 상한 없음. 렉시오처럼 모든 두 사람이 서로 정산한다.
    ① 각자 벌점 = max(0, 남은 타일 점수 − 자기 꽃잎 수) × 5^doubles × 2^(남은 13 장수). 1등(손패 0장)은 0.
    ② 모든 두 사람 사이에서 벌점이 큰 쪽이 작은 쪽에게 차이만큼 준다.
    ③ 보너스 1점마다 나머지 세 사람이 그 사람에게 1점씩 준다(합계 0)."""
    mult = TODAY_MULT**doubles
    pen = [
        max(0, sum(TILE_POINTS[t] for _, t in h) - len(petals[i]))
        * mult
        * 2 ** sum(t == 13 for _, t in h)
        for i, h in enumerate(hands_left)
    ]
    n = len(hands_left)
    delta = [sum(pen) - n * p for p in pen]
    for i, b in enumerate(bonus):
        for j in range(n):
            if j != i:
                delta[j] -= b
                delta[i] += b
    return delta


def run_case(case):
    tiles = lambda xs: [parse(x) for x in xs]
    t = case["type"]
    if t == "classify":
        got = classify(tiles(case["tiles"]))
        return got[0] if got else None
    if t == "beats":
        return beats(tiles(case["prev"]), tiles(case["new"]))
    if t == "first_player":
        return first_player([tiles(h) for h in case["hands"]])
    if t == "simulate":
        r = simulate(
            [tiles(h) for h in case["hands"]],
            [m if m == "패스" else tiles(m) for m in case["moves"]],
            case["today"],
        )
        return {k: r[k] for k in case["expect"]}
    if t == "settle":
        return settle(
            [tiles(h) for h in case["hands_left"]],
            case["petals"],
            case["bonus"],
            case["doubles"],
        )
    raise ValueError(t)


def full_count():
    got = Counter()
    for hand in combinations(DECK, 5):
        c = classify(list(hand))
        got[c[0] if c else None] += 1
    return got


if __name__ == "__main__":
    cases = json.loads((Path(__file__).parent / "cases.json").read_text())
    fails = 0
    for case in cases:
        got = run_case(case)
        ok = got == case["expect"]
        fails += not ok
        note = f" [{case['decision']}]" if case.get("decision") else ""
        print(
            f"{'PASS' if ok else 'FAIL'} {case['id']}{note}"
            + ("" if ok else f"  기대 {case['expect']!r} / 실제 {got!r}")
        )
    print(f"\n{len(cases) - fails}/{len(cases)} 통과")
    if "--full" in sys.argv:
        got = full_count()
        expect = json.loads((Path(__file__).parent / "full_count.json").read_text())
        for k, v in expect.items():
            ok = got[k] == v
            fails += not ok
            print(f"{'PASS' if ok else 'FAIL'} 전수 {k}: 기대 {v} / 실제 {got[k]}")
    sys.exit(1 if fails else 0)
