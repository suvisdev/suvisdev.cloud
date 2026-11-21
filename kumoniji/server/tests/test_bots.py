import random

from kumoniji.bots import mask, pick, seen, turns
from kumoniji.game import Game


def test_turns_counts_fewest_plays():
    assert turns(mask([("솜", 5), ("잎", 5), ("벚", 6)])) == 2  # 5 페어 + 6
    straight = {("솜", 1), ("잎", 2), ("벚", 3), ("산", 4), ("솜", 5)}
    assert turns(mask(straight | {("산", 9)})) == 2


def test_normal_keeps_its_pair_when_following():
    g = Game(
        hands=[
            [("솜", 5), ("잎", 5), ("벚", 6)],
            [("솜", 1)],
            [("솜", 2)],
            [("솜", 3)],
        ],
        today="산",
        turn=0,
        table=[("산", 4)],
        last=3,
    )
    assert pick("normal", seen(g, 0), random.Random(0)) == [
        ("벚", 6)
    ]  # 가장 약한 솜5는 페어를 깬다


def test_bots_do_not_see_who_holds_which_tile(monkeypatch):
    """남의 손패를 자리끼리 바꿔도(장수는 같게) 봇의 수는 같다 — 봇은 안 나온 패 전체만 안다."""
    from kumoniji import bots

    monkeypatch.setattr(
        bots, "BUDGET", float("inf")
    )  # 시간 상한에 걸리면 나눠 본 횟수가 달라 수가 바뀔 수 있다
    rng = random.Random(7)
    for _ in range(30):
        g = Game.deal(rng)
        while (
            sum(map(len, g.hands)) > 18 and g.winner is None
        ):  # hard가 끝판 계산을 하는 구간까지
            g.play(g.turn, pick("normal", seen(g, g.turn), rng))
        if g.winner is not None:
            continue
        me = g.turn
        others = [i for i in range(4) if i != me]
        pool = [t for i in others for t in g.hands[i]]
        rng.shuffle(pool)
        h = Game(**{**g.__dict__, "hands": [list(x) for x in g.hands]})
        k = 0
        for i in others:
            h.hands[i], k = pool[k : k + len(g.hands[i])], k + len(g.hands[i])
        for level in ("easy", "normal", "hard"):
            assert pick(level, seen(g, me), random.Random(1)) == pick(
                level, seen(h, me), random.Random(1)
            )


def test_hard_endgame_respects_time_budget(monkeypatch):
    """끝판 계산은 시간 상한을 넘기면 최소 4번만 나눠 보고 멈춘다(봇 한 수 0.5초 기준)."""
    from kumoniji import bots

    calls = []
    monkeypatch.setattr(bots, "BUDGET", 0.0)
    monkeypatch.setattr(bots, "_rollout", lambda s, hands, m: calls.append(m) or 0)
    g = Game(
        hands=[
            [("솜", 2), ("잎", 5), ("벚", 9)],
            [("솜", 3), ("산", 4)],
            [("잎", 3), ("산", 6)],
            [("벚", 3), ("산", 8)],
        ],
        today="산",
        turn=0,
        table=[("솜", 1)],
        last=3,
    )
    s = seen(g, 0)
    legal = [[("솜", 2)], [("잎", 5)], [("벚", 9)]]
    bots.endgame(s, legal, random.Random(0))
    assert len(calls) == 4 * len(bots._candidates(s, legal))
