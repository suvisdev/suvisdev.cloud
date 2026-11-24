"""봇 난이도 하네스(PRODUCT.md §3 완성 기준). 시드 고정, 재는 봇의 자리는 판마다 돌린다.
실행: cd kumoniji/server && python -m kumoniji.bench [판 수=1000]
기준: normal 1 + easy 3에서 normal 1등 ≥40%, hard 1 + normal 3에서 hard 1등 ≥40%(우연 25%),
      평균 점수도 재는 봇이 가장 높고, 봇 한 수가 0.5초 안."""

import random
import sys
import time

from .bots import pick, seen
from .game import Game


def match(top: str, rest: str, games: int, seed: int = 20261121) -> dict:
    rng = random.Random(seed)
    wins, chips, slow = 0, [0, 0], 0.0
    for i in range(games):
        g, me = Game.deal(rng), i % 4
        levels = [top if s == me else rest for s in range(4)]
        while g.winner is None:
            t = time.perf_counter()
            m = pick(levels[g.turn], seen(g, g.turn), rng)
            slow = max(slow, time.perf_counter() - t)
            g.play(g.turn, m)
        score = g.settlement()
        wins += g.winner == me
        chips[0] += score[me]
        chips[1] += sum(score) - score[me]  # 합이 0이라 = -score[me], 상대 셋 평균은 /3
    return {
        "win": wins / games,
        "chip_top": chips[0] / games,
        "chip_rest": chips[1] / games / 3,
        "slowest": slow,
    }


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    for top, rest in [("normal", "easy"), ("hard", "normal"), ("hard", "easy")]:
        t = time.perf_counter()
        r = match(top, rest, n)
        print(
            f"{top} 1 + {rest} 3, {n}판: 1등 {r['win']:.1%} · 평균 점수 {r['chip_top']:+.1f} 대 {r['chip_rest']:+.1f}"
            f" · 가장 느린 한 수 {r['slowest']:.3f}초 · {time.perf_counter() - t:.0f}초"
        )
