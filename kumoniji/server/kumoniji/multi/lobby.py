"""자동 매칭 대기열 + 친구방 + 진행 중 판 목록(계획 C Task 3·4). 입출력 없는 순수 로직 — 보내기는 ws.py가 한다.
한 이벤트 루프에서만 부르므로 잠금이 없다(replicas 1, 메모리 저장 — ADR-0023)."""

import random
import secrets
from dataclasses import dataclass, field, replace
from itertools import count

from .table import MultiTable

CODE_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # 헷갈리는 0/O/1/I 제외
ROOM_IDLE = 30 * 60  # 시작 안 한 방을 지우는 시간
JOIN_FAILS = 10  # 계정당 분당 잘못된 코드 허용 횟수(코드 대입 방지)


class LobbyError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class Player:
    account: int
    name: str
    ip: str = ""
    device: str = ""
    seq: int = 0  # 대기열에 들어온 순번 — 판을 거둘 때 원래 대기 순서로 되돌린다(Lobby.abort)


@dataclass
class Room:
    code: str
    created: float
    members: list[Player] = field(default_factory=list)  # 0번이 방장


def _completes(chosen: list[Player], rest: list[Player]) -> bool:
    """chosen에 rest에서 몇 명을 더해 네 명(IP·기기 모두 다름)을 채울 수 있나.
    사람 = 'IP—기기' 사이의 선으로 보면 이분 그래프 매칭이다. 증가 경로(Kuhn)로 찾고, 실패한 탐색의 방문 표시를
    다음 IP에도 이어 써서(성공할 때만 지움) rest 길이에 비례하는 시간에 끝난다."""
    need = 4 - len(chosen)
    if need <= 0:
        return True

    def dev(q: Player) -> tuple:  # 기기 모름(웹)은 누구와도 안 겹친다 — 앱 기기 값과 섞이지 않게 종류를 붙인다
        return ("device", q.device) if q.device else ("none", q.account)

    by_ip: dict[str, list[Player]] = {}
    for q in rest:
        if all(_apart(q, c) for c in chosen):
            by_ip.setdefault(q.ip, []).append(q)
    match: dict[tuple, Player] = {}
    seen: set[tuple] = set()

    def augment(ip: str) -> bool:
        for q in by_ip[ip]:
            if (d := dev(q)) in seen:
                continue
            seen.add(d)
            if d not in match or augment(match[d].ip):
                match[d] = q
                return True
        return False

    for ip in by_ip:
        if augment(ip):
            seen.clear()
            if len(match) == need:
                return True
    return False


def _apart(x: Player, y: Player) -> bool:
    """자동 매칭에서 같은 판에 넣어도 되는 두 사람 — IP가 다르고, 기기를 알면 기기도 달라야 한다(웹은 기기 모름)."""
    return x.ip != y.ip and not (x.device and x.device == y.device)


class Lobby:
    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random(secrets.randbits(64))
        self.queue: list[Player] = []
        self.rooms: dict[str, Room] = {}
        self.tables: dict[str, MultiTable] = {}
        self.table_of: dict[int, str] = {}  # 계정 → 판 id
        self.fails: dict[int, list[float]] = {}
        self._seq = count(1)

    # ── 어디에 있나 ──
    def table_for(self, account: int, now: float) -> MultiTable | None:
        """진행 중인 판(공개됐고 끝나지도 무효도 아닌). 끝난 판에 있던 사람은 다시 매칭할 수 있다."""
        t = self.pending_for(account, now)
        return t if t is not None and t.ready else None

    def pending_for(self, account: int, now: float) -> MultiTable | None:
        """끝나지도 무효도 아닌 판 — 하트를 쓰는 중이라 아직 공개 전인 판도 포함."""
        t = self.tables.get(self.table_of.get(account, ""))
        if t is None or t.game.winner is not None or t.void(now):
            return None
        return t

    def finished_for(self, account: int, now: float) -> MultiTable | None:
        """끝났지만 아직 보관 중인 판(결과를 못 보고 끊긴 사람이 다시 붙을 때)."""
        t = self.tables.get(self.table_of.get(account, ""))
        return t if t is not None and t.game.winner is not None and not t.expired(now) else None

    def room_of(self, account: int) -> Room | None:
        return next((r for r in self.rooms.values() if any(p.account == account for p in r.members)), None)

    def _free(self, account: int, now: float) -> None:
        if self.pending_for(account, now):  # 하트를 쓰는 중인 판도 — 그사이 다른 판에 들어가지 않게
            raise LobbyError("in_game")
        if any(p.account == account for p in self.queue):
            raise LobbyError("in_queue")
        if self.room_of(account):
            raise LobbyError("in_room")

    def _start(self, players: list[Player], now: float, kind: str, room: Room | None = None) -> MultiTable:
        """판을 만든다(아직 공개 전 — 하트를 다 쓰면 reveal, 모자라면 abort)."""
        names = [p.name for p in players]
        t = MultiTable([p.account for p in players], names, now, random.Random(self.rng.random()), kind, ready=False)
        t.players, t.room = players, room  # 거둘 때 대기열·방으로 되돌리려고
        self.tables[t.id] = t
        for p in players:
            self.table_of[p.account] = t.id
        return t

    def abort(self, t: MultiTable, out: set[int], now: float) -> list[MultiTable]:
        """하트가 모자라 판을 거둔다(ADR-0024 B안). 모자란 사람(out)과 쓰는 중 취소한 사람(t.leaving)은 빠지고, 나머지는
        자동 매칭이면 대기열의 원래 순번 자리로(기다린 시간을 잃지 않게), 친구방이면 방을 그대로 되살린다.
        되돌린 대기열로 바로 네 명씩 맞춰지는 판(역시 공개 전)을 모두 돌려준다. 보통은 돌아온 사람끼리 안 겹쳐 첫 판이 모두
        데려가지만, 쓰는 중 다른 IP로 다시 붙은 사람(update)이 있으면 둘이 겹쳐 두 판이 될 수 있다(리뷰 지적)."""
        if self.tables.get(t.id) is not t:
            return []
        del self.tables[t.id]
        for a in t.accounts:
            if self.table_of.get(a) == t.id:
                del self.table_of[a]
        out = out | t.leaving
        back = [p for p in t.players if p.account not in out]
        if t.room is not None:
            if back:
                t.room.members = [m for m in t.room.members if m.account not in out]
                self.rooms[t.room.code] = t.room
            return []
        self.queue = sorted(back + self.queue, key=lambda q: q.seq)  # 원래 대기 순서 자리로(먼저 기다린 사람보다 앞서지 않게)
        made = []
        for p in back:
            if p in self.queue and (nt := self._match(p, now)):  # 앞 판에 이미 들어간 사람은 건너뛴다
                made.append(nt)
        return made

    def cancel_pending(self, account: int) -> None:
        """하트를 쓰는 중인 판(공개 전)에서 직접 취소(unqueue·room.leave) → 표시만 해 두고 거둘 때 되돌리지 않는다.
        쓰기가 성공하면 판은 그대로 열린다. 끊김(disconnect)은 여기로 오지 않는다 — 다시 붙으면 되돌린다(_charge가 그때 판단)."""
        t = self.tables.get(self.table_of.get(account, ""))
        if t is not None and not t.ready:
            t.leaving.add(account)

    # ── 자동 매칭 ──
    def enqueue(self, p: Player, now: float) -> MultiTable | None:
        """대기열 앞에서부터 IP·기기가 겹치지 않는 4명이 모이면 판을 만든다(같은 사람 여러 창 방지).
        직전 판 상대를 피하지는 않는다 — 계획 C의 '판마다 새로 매칭'은 끝나면 다시 눌러야 한다는 뜻이고,
        사람이 적을 때 같은 상대를 막으면 판이 아예 안 열린다."""
        self._free(p.account, now)
        p = replace(p, seq=next(self._seq))
        self.queue.append(p)
        return self._match(p, now)

    def _match(self, p: Player, now: float) -> MultiTable | None:
        if picked := self._group(p):
            picked = [q for q in self.queue if q in picked]  # 대기열 순서로(거둘 때 그 순서로 되돌린다)
            self.queue = [q for q in self.queue if q not in picked]
            return self._start(picked, now, "auto")
        return None

    def _group(self, p: Player) -> list[Player] | None:
        """p와 함께 놓일 세 명 — IP도 기기도 서로 겹치지 않게. 새 사람(또는 IP가 바뀐 사람)이 생겨야만 새 조합이 생긴다.
        오래 기다린 사람부터 '이 사람을 넣어도 네 명을 채울 수 있나'를 보고 되면 넣는다(선착순).
        채울 수 있는지는 이분 매칭(사람 = IP—기기 선)으로 본다 — 있으면 반드시 찾는다."""
        cands = [q for q in self.queue if q.account != p.account and _apart(q, p)]
        if not _completes([p], cands):  # 조합이 아예 없으면 한 번 보고 끝(대기열 길이에 비례)
            return None
        chosen = [p]
        # IP·기기가 같은 사람끼리는 서로 바꿔도 결과가 같다. 고른 사람이 늘수록 채우기는 어려워지기만 하므로,
        # 한 번 '안 됨'이 나온 묶음은 끝까지 안 된다 — 다시 따지지 않는다(같은 묶음이 몰려도 제곱으로 안 커짐).
        hopeless: set[tuple[str, str]] = set()
        for i, q in enumerate(cands):
            if len(chosen) == 4:
                break
            if (q.ip, q.device) in hopeless or not all(_apart(q, c) for c in chosen):
                continue
            if _completes([*chosen, q], cands[i + 1 :]):
                chosen.append(q)
            else:
                hopeless.add((q.ip, q.device))
        return chosen

    def update(self, p: Player, now: float) -> MultiTable | None:
        """대기 중 다시 붙음 → 새 IP·기기로 바꾸고, 그 덕에 네 명이 맞춰지면 판을 만든다.
        하트를 쓰는 중인 판(공개 전)에 있으면 그 판의 정보도 바꾼다 — 거둘 때 그 정보로 대기열에 돌아간다(abort)."""
        t = self.pending_for(p.account, now)
        if t is not None and not t.ready:
            t.players = [replace(p, seq=q.seq) if q.account == p.account else q for q in t.players]
        old = next((q for q in self.queue if q.account == p.account), None)
        if old is None:
            return None
        p = replace(p, seq=old.seq)  # 다시 붙어도 대기 순서는 그대로
        self.queue = [p if q is old else q for q in self.queue]
        return self._match(p, now)

    def unqueue(self, account: int) -> bool:
        """대기열에서 뺀다. 실제로 있었으면 True(그때만 남은 대기자에게 알린다)."""
        before = len(self.queue)
        self.queue = [q for q in self.queue if q.account != account]
        return len(self.queue) != before

    # ── 친구방(IP 제한 없음 — 같은 집 친구) ──
    def create_room(self, p: Player, now: float) -> Room:
        self._free(p.account, now)
        while (code := "".join(secrets.choice(CODE_CHARS) for _ in range(6))) in self.rooms:
            pass
        r = self.rooms[code] = Room(code, now, [p])
        return r

    def join_room(self, p: Player, code: str, now: float) -> Room:
        recent = [t for t in self.fails.get(p.account, []) if now - t < 60]
        self.fails[p.account] = recent
        if len(recent) >= JOIN_FAILS:
            raise LobbyError("too_many")
        self._free(p.account, now)
        r = self.rooms.get(code.strip().upper())
        if r is None:
            recent.append(now)
            raise LobbyError("no_room")
        if len(r.members) >= 4:
            raise LobbyError("room_full")
        r.members.append(p)
        return r

    def leave_room(self, account: int) -> Room | None:
        """방에서 나감. 방장이 나가면 다음 사람이 방장, 빈 방은 지운다. 남은 방(알림용)을 돌려준다."""
        r = self.room_of(account)
        if r is None:
            return None
        r.members = [m for m in r.members if m.account != account]
        if not r.members:
            del self.rooms[r.code]
            return None
        return r

    def start_room(self, account: int, now: float) -> MultiTable:
        r = self.room_of(account)
        if r is None:
            raise LobbyError("no_room")
        if r.members[0].account != account:
            raise LobbyError("not_host")
        if len(r.members) != 4:
            raise LobbyError("need_four")
        del self.rooms[r.code]
        players = list(r.members)
        self.rng.shuffle(players)  # 자리 무작위
        return self._start(players, now, "room", r)

    # ── 끊김·정리 ──
    def disconnect(self, account: int, now: float) -> tuple[MultiTable | None, Room | None]:
        """연결이 끊기면 대기열·방에서 빠진다. 판에서는 빠지지 않는다(타이머가 패스, 다시 붙으면 이어서)."""
        self.unqueue(account)
        room = self.leave_room(account)
        t = self.pending_for(account, now)  # 공개 전 판도 끊김 표시(공개되면 그대로 이어진다)
        if t:
            t.set_connected(account, False, now)
        return t, room

    def sweep(self, now: float) -> list[int]:
        """끝난·무효 판, 30분 지난 방, 오래된 실패 기록을 지운다. 지운 방에 있던 계정을 돌려준다(알림용)."""
        gone: list[int] = []
        for tid in [tid for tid, t in self.tables.items() if t.expired(now)]:
            t = self.tables.pop(tid)
            for a in t.accounts:
                if self.table_of.get(a) == tid:
                    del self.table_of[a]
        for code in [c for c, r in self.rooms.items() if now - r.created >= ROOM_IDLE]:
            gone += [m.account for m in self.rooms.pop(code).members]
        self.fails = {a: ts for a, ts in self.fails.items() if any(now - t < 60 for t in ts)}
        return gone
