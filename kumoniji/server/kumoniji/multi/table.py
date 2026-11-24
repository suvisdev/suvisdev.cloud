"""멀티 판 하나: Game(서버 권위) + 자리별 계정 + 차례 20초(넘기면 자동 패스). 계획 C Task 2.
시간은 부르는 쪽이 now(에포크 초)로 넘긴다 — 운영은 time.time(), 테스트는 가짜 시계.
판을 진행하는 메서드는 그 판에서 새로 생긴 수(events)를 돌려주고, 보내기는 부르는 쪽(ws)이 한다."""

import random
import secrets

from fastapi import HTTPException

from ..bots import can_beat
from ..game import Game, IllegalMove
from ..view import dec, enc, reason, view

TURN = 20  # 차례마다 초
GONE = 180  # 네 명 모두 끊긴 채 이만큼 지나면 판 무효·제거
KEEP = 600  # 끝난 판을 결과 화면용으로 남겨 두는 시간


class NotYourTurn(Exception):
    pass


class Illegal(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class MultiTable:
    def __init__(self, accounts: list[int], names: list[str], now: float, rng: random.Random | None = None):
        assert len(accounts) == 4 and len(set(accounts)) == 4
        self.id = secrets.token_urlsafe(12)
        self.game = Game.deal(rng or random.Random(secrets.randbits(64)))
        self.accounts, self.names = accounts, names
        self.connected = [True] * 4
        self.gone_since: float | None = None  # 네 명 모두 끊긴 때
        self.finished_at: float | None = None
        self.deadline = now + TURN
        self.ply = 0  # 지금까지 처리한 수(패스 포함) — 앱은 이 번호를 붙여 내고, 다르면 늦게 온 옛 수로 거부
        self._auto(now)

    def seat_of(self, account: int) -> int | None:
        return self.accounts.index(account) if account in self.accounts else None

    def _record(self, seat: int, tiles: list | None, now: float) -> dict:
        self.game.play(seat, tiles)
        self.ply += 1
        e = {"seat": seat, "tiles": [enc(t) for t in tiles] if tiles else None}
        if self.game.winner is not None:
            self.finished_at = now
        self.deadline = now + TURN
        return e

    def _auto(self, now: float) -> list[dict]:
        """아무도(모든 손패를 합쳐도) 바닥을 이길 수 없으면 그 차례를 바로 패스시킨다 — 싱글의 사람 자동 패스와 같다.
        자기 손패가 아니라 공개 정보로만 판단해 '저 사람은 낼 패가 없다'가 드러나지 않는다."""
        out = []
        g = self.game
        # 패스는 바닥·손패를 바꾸지 않으니 한 바퀴(바닥이 비기 전)엔 한 번만 판정한다(판정은 최악 1ms 안 — bots._can_beat5).
        if g.winner is None and g.table and not can_beat(g.table, [t for h in g.hands for t in h]):
            while g.winner is None and g.table:
                out.append(self._record(g.turn, None, now))
        return out

    def move(self, account: int, codes: list[str], now: float, ply: int | None = None) -> list[dict]:
        """account가 낸 패(빈 목록 = 패스). 그 자리 차례가 아니면 NotYourTurn, 낼 수 없으면 Illegal(code).
        ply: 그 수를 낼 때 본 상태의 번호. 다르면(그새 자동 패스·다른 수가 지나감) 늦게 온 옛 수라 거부한다."""
        seat, g = self.seat_of(account), self.game
        if ply is not None and ply != self.ply:
            raise NotYourTurn
        # 마감이 지난 수는 받지 않는다 — 타이머(tick)보다 먼저 처리되면 자동 패스를 건너뛰게 된다
        if seat is None or self.void(now) or g.winner is not None or g.turn != seat or now >= self.deadline:
            raise NotYourTurn
        try:
            tiles = [dec(c) for c in codes]
        except HTTPException:  # dec: 잘못된 표기
            raise Illegal("bad_tile") from None
        try:
            out = [self._record(seat, tiles or None, now)]
        except IllegalMove:
            raise Illegal(reason(g, tiles, seat)) from None
        return out + self._auto(now)

    def tick(self, now: float) -> list[dict]:
        """마감이 지났으면 그 차례를 자동 패스(선이어도 — 계획 A). 끊긴 사람도 같은 규칙."""
        if self.void(now) or self.game.winner is not None or now < self.deadline:
            return []
        return [self._record(self.game.turn, None, now), *self._auto(now)]

    def set_connected(self, account: int, on: bool, now: float) -> None:
        seat = self.seat_of(account)
        if seat is None or self.void(now):  # 무효가 된 판은 다시 붙어도 살리지 않는다(곧 제거된다)
            return
        self.connected[seat] = on
        if any(self.connected):
            self.gone_since = None
        elif self.gone_since is None:  # 0.0도 유효한 시각이라 `or`로 쓰지 않는다
            self.gone_since = now

    def void(self, now: float) -> bool:
        """네 명 모두 끊긴 채 GONE초 — 판 무효. 그 뒤로는 수·타이머·재접속 모두 판을 바꾸지 않는다."""
        return self.game.winner is None and self.gone_since is not None and now - self.gone_since >= GONE

    def expired(self, now: float) -> bool:
        """메모리에서 지울 때: 무효가 됐거나, 끝난 지 KEEP초."""
        if self.finished_at is not None:
            return now - self.finished_at >= KEEP
        return self.void(now)

    def state(self, seat: int, events: list[dict]) -> dict:
        """seat 자리에게 보낼 상태 — 싱글 view와 같은 모양(손패는 자기 것만) + 멀티 정보."""
        return {
            "t": "state",
            **view(self.id, self.game, events, seat=seat),
            "seat": seat,
            "names": list(self.names),
            "deadline": None if self.game.winner is not None else self.deadline,
            "ply": self.ply,
            "connected": list(self.connected),  # 복사 — 보내기 전에 연결이 바뀌어도 이 상태는 그대로
        }
