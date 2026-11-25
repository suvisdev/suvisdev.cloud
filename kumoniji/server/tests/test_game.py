import json
import random
from pathlib import Path

import pytest

from kumoniji import rules
from kumoniji.bots import pick, seen
from kumoniji.game import Game, IllegalMove

CASES = [
    c
    for c in json.loads((Path(rules.__file__).parent / "cases.json").read_text())
    if c["type"] == "simulate"
]
P = rules.parse


def replay(hands, moves, today):
    g = Game(
        hands=[list(h) for h in hands], today=today, turn=rules.first_player(hands)
    )
    for i, m in enumerate(moves):
        try:
            g.play(g.turn, m)
        except IllegalMove:
            return g, i
    return g, None


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_matches_simulate_cases(case):
    hands = [[P(t) for t in h] for h in case["hands"]]
    moves = [None if m == "패스" else [P(t) for t in m] for m in case["moves"]]
    g, err = replay(hands, moves, case["today"])
    got = {
        "error_at": err,
        "winner": g.winner,
        "petals": g.petals,
        "bonus": g.bonus,
        "doubles": g.doubles,
        "hands": g.hands,
    }
    assert {k: got[k] for k in case["expect"]} == case["expect"]


def test_leader_pass_hands_the_lead_on_and_wrong_seat():
    g = Game(
        hands=[[("산", 1)], [("산", 2)], [("산", 3)], [("산", 4)]], today="벚", turn=0
    )
    with pytest.raises(IllegalMove):
        g.play(1, [("산", 2)])
    g.play(0, None)  # 선도 패스할 수 있다(11-21) — 바닥은 빈 채로 1번이 선
    assert (g.turn, g.table, g.passes, g.last) == (1, [], 0, None)
    g.play(1, [("산", 2)])
    assert g.winner == 1


@pytest.mark.parametrize(
    "levels,games",
    [
        (("easy", "normal", "easy", "normal"), 500),
        (("hard", "normal", "easy", "hard"), 40),
    ],
)
def test_bot_games_match_simulate_and_zero_sum(levels, games):
    rng = random.Random(20261118)
    for _ in range(games):
        g = Game.deal(rng)
        start = [list(h) for h in g.hands]
        moves = []
        while g.winner is None:
            m = pick(levels[g.turn], seen(g, g.turn), rng)
            if not g.table and rng.random() < 0.1:
                m = None  # 사람이 선에서 패스하는 경우도 섞는다(봇은 선 패스를 안 함)
            moves.append("패스" if m is None else m)
            g.play(g.turn, m)
        r = rules.simulate(start, moves, g.today)
        assert (r["error_at"], r["winner"], r["petals"], r["bonus"], r["doubles"]) == (
            None,
            g.winner,
            g.petals,
            g.bonus,
            g.doubles,
        )
        assert sum(g.settlement()) == 0


def test_stats_count_combos_and_today_rounds():
    def T(text):
        return [P(x) for x in text.split()]

    hands = [T("벚3 잎3 산3 솜5 솜6 솜7 솜8 솜9 잎13"), T("솜1 솜2"), T("잎1 잎2"), T("산1 산2")]
    g = Game(hands=hands, today="솜", turn=0)
    g.play(0, T("벚3 잎3 산3"))  # 트리플
    for s in (1, 2, 3):
        g.play(s, None)  # 셋 다 패스 → 0번이 바퀴를 가져감(오늘의 무늬 없음)
    g.play(0, T("솜5 솜6 솜7 솜8 솜9"))  # 5장(스트레이트플러시)
    for s in (1, 2, 3):
        g.play(s, None)  # 오늘의 무늬(솜)가 든 패로 가져감
    assert g.stats[0] == {"five": 1, "triple": 1, "oddeven": 0, "fullhouse": 0, "today": 1}
    assert g.stats[1] == {"five": 0, "triple": 0, "oddeven": 0, "fullhouse": 0, "today": 0}


def test_finishing_with_today_shape_counts_as_taking_the_round():
    g = Game(hands=[[("솜", 5)], [("산", 1)], [("산", 2)], [("산", 3)]], today="솜", turn=0)
    g.play(0, [("솜", 5)])
    assert g.winner == 0 and g.stats[0]["today"] == 1
