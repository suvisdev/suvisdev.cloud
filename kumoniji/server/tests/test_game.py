import json
import random
from pathlib import Path

import pytest

from kumoniji import rules
from kumoniji.bots import pick
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


def test_leader_cannot_pass_and_wrong_seat():
    g = Game(
        hands=[[("산", 1)], [("산", 2)], [("산", 3)], [("산", 4)]], today="벚", turn=0
    )
    with pytest.raises(IllegalMove):
        g.play(0, None)
    with pytest.raises(IllegalMove):
        g.play(1, [("산", 2)])


def test_bot_games_match_simulate_and_zero_sum():
    rng = random.Random(20261118)
    for _ in range(500):
        g = Game.deal(rng)
        start = [list(h) for h in g.hands]
        moves = []
        while g.winner is None:
            m = pick("aim", g.hands[g.turn], g.table, g.today, rng)
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
