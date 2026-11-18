"""한 판 진행 상태(서버 권위). rules.simulate와 같은 규칙을 한 수씩 적용한다."""

import random
from dataclasses import dataclass, field

from .rules import (
    DECK,
    SHAPES,
    beats,
    first_player,
    settle,
    small_today,
    special_steps,
    value,
)

Tile = tuple[str, int]


class IllegalMove(ValueError):
    pass


@dataclass
class Game:
    hands: list[list[Tile]]
    today: str
    turn: int
    table: list[Tile] = field(default_factory=list)
    last: int | None = None
    passes: int = 0
    petals: list[list[str]] = field(default_factory=lambda: [[] for _ in range(4)])
    bonus: list[int] = field(default_factory=lambda: [0] * 4)
    pot: int = 0
    doubles: int = 0
    winner: int | None = None
    # 이번 바퀴에서 바닥 패 이전에 나온 수(자리, 패) — 화면에서 자리마다 낸 패를 보여 주는 용도, 규칙엔 안 쓰임
    history: list[tuple[int, list[Tile]]] = field(default_factory=list)

    @classmethod
    def deal(cls, rng: random.Random) -> "Game":
        deck = DECK[:]
        rng.shuffle(deck)
        hands = [sorted(deck[i * 13 : (i + 1) * 13], key=value) for i in range(4)]
        return cls(hands=hands, today=rng.choice(SHAPES), turn=first_player(hands))

    def play(self, seat: int, move: list[Tile] | None) -> None:
        if self.winner is not None or seat != self.turn:
            raise IllegalMove("차례가 아님")
        n = len(self.hands)
        if move is None:
            if not self.table:
                raise IllegalMove("선은 패스할 수 없음")
            self.passes += 1
            if self.passes == n - 1:
                self.petals[self.last].append(max(self.table, key=value)[0])
                self.bonus[self.last] += self.pot + small_today(self.table, self.today)
                self.table, self.passes, self.pot = [], 0, 0
                self.history = []
        else:
            if any(t not in self.hands[seat] for t in move) or not beats(
                self.table, move
            ):
                raise IllegalMove("낼 수 없는 패")
            for t in move:
                self.hands[seat].remove(t)
            self.pot += special_steps(move, self.today, finish=not self.hands[seat])
            self.doubles += len(move) == 5 and all(s == self.today for s, _ in move)
            if self.table:
                self.history.append((self.last, self.table))
            self.table, self.last, self.passes = list(move), seat, 0
            if not self.hands[seat]:
                self.bonus[seat] += self.pot + small_today(move, self.today)
                self.pot, self.winner = 0, seat
                return
        self.turn = (self.turn + 1) % n

    def settlement(self) -> list[int] | None:
        return (
            None
            if self.winner is None
            else settle(self.hands, self.petals, self.bonus, self.doubles)
        )
