"""/api/ws — 멀티 WebSocket(계획 C Task 5). 메시지는 JSON 한 줄, 프로토콜은 계획 C '프로토콜' 절.
인증: 웹은 Origin == 공개 원점 + 쿠키, 앱은 Origin 없이 연결 직후 {"t":"auth","token":...}.
제한: 계정당 연결 1개(새 연결이 옛 연결을 닫음), 메시지 2KB·초당 10개, 유휴 60초, 60초마다 세션 재확인(로그아웃·폐기면 닫음).
보내기: 연결마다 보낼 줄(OUT)과 전용 작업(_writer). send()는 줄에 넣기만 해서 기다리지 않는다 — 타이머·다른 판이
느린 연결에 붙잡히지 않고, 한 연결에는 만든 순서대로 나간다."""

import asyncio
import json
import logging
import time
from collections import deque

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..accounts import sessions, web
from .lobby import Lobby, LobbyError, Player, Room
from .table import Illegal, MultiTable, NotYourTurn

log = logging.getLogger("kumoniji.ws")
router = APIRouter()
LOBBY = Lobby()
CONNS: dict[int, WebSocket] = {}
OUT: dict[WebSocket, asyncio.Queue] = {}
SESS: dict[WebSocket, dict] = {}  # 연결별 세션(토큰 만료 시각 exp 포함)
LAST_Q: dict[int, int] = {}  # 계정별 마지막으로 보낸 대기 인원
QUEUE_DIRTY = False
MAX_BYTES, RATE, IDLE, RECHECK, AUTH_WAIT = 2048, 10, 60.0, 55.0, 5.0  # 재확인 55초 + DB 대기 5초 ≤ 로그아웃 뒤 60초  # 프레임 크기 자체는 uvicorn --ws-max-size가 먼저 막는다(Dockerfile)
DB_SLOTS = {"auth": 3, "recheck": 2}
RENEW_AHEAD = 60.0  # 토큰 만료 이만큼 전에 {"t":"renew"} 안내
PENDING: dict[str, int] = {}  # IP별 인증 중인 연결 수
PENDING_MAX, PENDING_PER_IP = 100, 5
SEND_WAIT, BACKLOG = 2.0, 64  # 한 메시지 보내기 시간 제한, 쌓인 메시지가 이만큼이면 그 연결을 닫는다
clock = time.time  # 판 시간(마감). 테스트는 가짜 시계로 바꾼다


async def _close(ws: WebSocket, code: int) -> None:
    try:
        await asyncio.wait_for(ws.close(code), SEND_WAIT)
    except Exception:  # 이미 닫혔거나 막힌 연결
        pass


def _drop(a: int, ws: WebSocket, code: int) -> None:
    """더 보내지 않고 닫는다. 이 연결이 아직 계정을 대표하면 닫히기를 기다리지 않고 바로 대기열·방에서 뺀다
    (그사이 매칭·시작이 끊긴 사람을 넣지 않게). 새 연결에 밀린 옛 연결이면 자리는 새 연결이 이어받는다.
    send() 안(다른 알림을 보내는 도중)에서 불리므로 남은 사람에게 보내는 알림은 다음 차례로 미룬다."""
    had = ws in OUT
    _leave(a, ws, notify_later=True)
    if had:
        asyncio.get_running_loop().create_task(_close(ws, code))


async def _writer(a: int, ws: WebSocket, q: asyncio.Queue) -> None:
    while True:
        msg = await q.get()
        s = SESS.get(ws)
        if s is None or time.time() >= s["exp"]:  # 계정을 더 대표하지 않거나 토큰 만료 — 쌓인 손패·상태도 안 보낸다
            _drop(a, ws, 4401)
            return
        try:
            await asyncio.wait_for(ws.send_json(msg), SEND_WAIT)
        except Exception:  # 끊겼거나 막힌 연결
            _drop(a, ws, 1011)
            return


def send(account: int, msg: dict) -> None:
    q = OUT.get(ws) if (ws := CONNS.get(account)) is not None else None
    if q is None:
        return
    if q.qsize() >= BACKLOG:
        _drop(account, ws, 1011)
    else:
        q.put_nowait(msg)


def push(t: MultiTable, events: list[dict]) -> None:
    for a, st in [(a, t.state(seat, events)) for seat, a in enumerate(t.accounts)]:  # 보내기 전에 다 만든다
        send(a, st)


def room_msg(r: Room, i: int) -> dict:
    """me = 받는 사람 자신의 칸(닉네임은 겹칠 수 있어 앱이 이걸로 내가 방장인지 안다)."""
    members = [{"nick": m.name, "host": k == 0} for k, m in enumerate(r.members)]
    return {"t": "room", "code": r.code, "members": members, "me": i}


def push_room(r: Room) -> None:
    """방 구성이 바뀜 → 모든 참가자에게."""
    for a, msg in [(m.account, room_msg(r, i)) for i, m in enumerate(r.members)]:  # 보내기 전에 다 만든다
        send(a, msg)


def push_queue() -> None:
    """대기 인원이 바뀜 — 바로 보내지 않고 표시만, 타이머(0.5초)가 한 번에 보낸다(입퇴장이 몰려도 사람당 한 통)."""
    global QUEUE_DIRTY
    QUEUE_DIRTY = True


def flush_queue() -> None:
    global QUEUE_DIRTY
    if not QUEUE_DIRTY:
        return
    QUEUE_DIRTY = False
    n = len(LOBBY.queue)
    waiting = {p.account for p in LOBBY.queue}
    for a in list(LAST_Q):
        if a not in waiting:
            del LAST_Q[a]
    for a in waiting:
        if LAST_Q.get(a) != n:  # 이미 같은 인원을 받은 사람에게는 다시 안 보낸다
            tell_queued(a)


def tell_queued(a: int) -> None:
    LAST_Q[a] = len(LOBBY.queue)
    send(a, {"t": "queued", "waiting": LAST_Q[a]})


async def tick_forever() -> None:
    """차례 20초 마감 → 자동 패스, 끝난·무효 판과 오래된 방 정리. api lifespan이 띄운다."""
    _slots.clear()  # 이 이벤트 루프용으로 새로(세마포어는 처음 기다린 루프에 묶인다)
    while True:
        await asyncio.sleep(0.5)
        try:
            now = clock()
            for t in list(LOBBY.tables.values()):
                if ev := t.tick(now):
                    push(t, ev)
            for a in LOBBY.sweep(now):  # 30분 지나 지운 방에 있던 사람
                send(a, {"t": "lobby"})
            flush_queue()
        except Exception:
            log.exception("멀티 타이머 실패")


_slots: dict[str, asyncio.Semaphore] = {}


def _db_slots(kind: str) -> asyncio.Semaphore:
    """소켓의 DB 조회 자리 — 새 연결 인증(auth)과 기존 연결 재확인(recheck)을 따로 둔다.
    합쳐 DB 풀(8)의 절반 남짓이라 로그인을 막지 않고, 인증이 몰려도 재확인이 밀려 멀쩡한 연결이 끊기지 않는다."""
    if kind not in _slots:
        _slots[kind] = asyncio.Semaphore(DB_SLOTS[kind])
    return _slots[kind]


async def _db(kind: str, fn, *args):
    """DB 조회를 스레드에서. 자리는 스레드가 실제로 끝날 때 돌려준다 — 부른 쪽이 시간 초과로 취소돼도
    이미 시작된 조회는 계속 돌므로, 그때 자리를 먼저 풀면 동시 조회가 자리 수를 넘는다."""
    slots = _db_slots(kind)
    await slots.acquire()
    job = asyncio.ensure_future(asyncio.to_thread(fn, *args))
    job.add_done_callback(lambda _: slots.release())
    return await asyncio.shield(job)


def _leave(a: int, ws: WebSocket, notify_later: bool = False) -> None:
    """이 연결이 계정을 대표하지 않게 됨 — 대기열·방에서 빼고 판에는 끊김 표시. 여러 번 불러도 한 번만 처리.
    notify_later: 상태는 지금 바꾸고 알림만 다음 차례에(알림을 보내는 도중 끼어들어 순서가 뒤집히지 않게)."""
    OUT.pop(ws, None)
    SESS.pop(ws, None)
    if CONNS.get(a) is not ws:
        return  # 이미 처리했거나 새 연결에 밀림(새 연결이 자리를 이어받는다)
    del CONNS[a]
    LAST_Q.pop(a, None)
    was_queued = any(p.account == a for p in LOBBY.queue)
    t, r = LOBBY.disconnect(a, clock())

    def notify() -> None:  # 미뤄 보낼 수 있으니 보낼 때 아직 있는 판·방인지 다시 본다(그사이 정리됐으면 안 보냄)
        if t and LOBBY.tables.get(t.id) is t and t.game.winner is None:  # 끊김 표시는 진행 중인 판에만 의미 있다
            push(t, [])
        if r and LOBBY.rooms.get(r.code) is r:
            push_room(r)
        if was_queued:
            push_queue()

    asyncio.get_running_loop().call_soon(notify) if notify_later else notify()


async def _recheck(s: dict) -> bool:
    """세션 재확인. 조회하는 사이 갱신으로 인증 버전이 바뀌었으면 옛 버전의 실패는 버리고 새 버전으로 다시 본다."""
    while True:
        snap = dict(s)  # 조회는 이 시점의 버전으로(스레드가 도중에 바뀐 값을 읽지 않게)
        ok = await _recheck_once(s, snap)
        if s.get("ver") == snap.get("ver"):
            return ok


async def _recheck_once(s: dict, snap: dict) -> bool:
    """세션 재확인 조회(최대 AUTH_WAIT초). 기다리는 사이 토큰이 만료되면 바로 실패(그사이 매칭돼 손패를 받지 않게) —
    만료 시각은 0.5초마다 다시 봐서, 그사이 갱신했으면 늘어난 시각을 따른다."""
    job = asyncio.ensure_future(_db("recheck", web.socket_alive, snap))
    job.add_done_callback(lambda j: j.cancelled() or j.exception())  # 버려진 조회의 예외 경고 막기
    deadline = time.monotonic() + AUTH_WAIT
    try:
        while True:
            left = min(deadline - time.monotonic(), s["exp"] - time.time())
            if left <= 0:
                return False
            done, _ = await asyncio.wait({job}, timeout=min(left, 0.5))
            if done:
                return not job.exception() and bool(job.result())
    finally:
        # 포기했거나 연결이 닫힘 → 아직 자리를 기다리던 조회는 취소(쌓여서 자리를 막지 않게).
        # 이미 스레드에서 도는 조회는 _db의 shield 덕에 계속 돌고, 끝날 때 자리를 돌려준다.
        job.cancel()


async def _watch(ws: WebSocket, s: dict) -> None:
    """RECHECK초마다 세션 재확인(수신 루프와 따로 — 루프가 DB를 기다리느라 수를 늦게 처리하지 않게), 그리고
    액세스 토큰 만료(탈취한 토큰으로 연결해 리프레시 없이 계속 쓰지 못하게 — 앱은 갱신한 토큰을 보내 이어 간다).
    끝났거나 늦으면(AUTH_WAIT) 대기열·방에서 바로 빼고 닫는다."""
    due = time.monotonic() + RECHECK
    hinted = None  # 갱신 안내를 보낸 만료 시각
    while True:
        until_exp = s["exp"] - time.time()
        if hinted != s["exp"]:  # 아직 안내 전 — 안내 시각까지(이미 지났으면 바로)
            nap = min(due - time.monotonic(), until_exp - RENEW_AHEAD)
        else:
            nap = min(due - time.monotonic(), until_exp)
        await asyncio.sleep(max(nap, 0))
        if time.time() >= s["exp"]:  # 그사이 갱신했으면 exp가 늘어 있다 — 끝까지 안 했으면 빠진다(탈취 토큰 차단)
            alive = False
        elif hinted != s["exp"] and s["exp"] - time.time() <= RENEW_AHEAD:
            hinted = s["exp"]  # 만료 전에 갱신하라고 한 번 알린다 — 앱은 새 토큰을 auth로, 웹은 쿠키 갱신 뒤 재연결(자리 유지)
            send(s["account_id"], {"t": "renew"})
            continue
        elif time.monotonic() >= due:
            due = time.monotonic() + RECHECK  # 조회 시작 기준 — 조회가 늦어도 다음 조회가 밀리지 않는다(최악 55+5초)
            alive = await _recheck(s)
        else:
            continue
        if not alive:
            _leave(s["account_id"], ws)  # 닫히기를 기다리지 않고 바로 대기열·방에서 뺀다
            await asyncio.shield(_close(ws, 4401))  # 수신 루프가 끝나며 이 작업을 취소해도 4401은 끝까지 보낸다
            return


async def _authenticate(ws: WebSocket, from_browser: bool) -> dict | None:
    token = ws.cookies.get(web.ACCESS) if from_browser else None
    if not token:
        try:
            raw = await ws.receive_text()  # 시간 제한은 부르는 쪽이 인증 전체에 건다
            first = json.loads(raw) if len(raw.encode()) <= MAX_BYTES else None
            token = first.get("token") if isinstance(first, dict) and first.get("t") == "auth" else None
        except Exception:  # 시간 초과·끊김·JSON 아님 → 인증 실패
            token = None
    if not isinstance(token, str) or (claims := sessions.decode(token)) is None:  # 서명이 틀린 토큰은 DB 자리를 안 씀
        return None
    s = await _db("auth", web.socket_session, token)
    return s and {**s, "exp": claims["exp"]}


def _renew(s: dict, token) -> bool:
    """연결 중 토큰 갱신({"t":"auth","token":새 토큰}) — 같은 계정·같은 세션의 서명이 맞는 토큰이면 만료 시각만 늘린다.
    폐기·비밀번호 변경은 재확인(_watch)이 잡는다."""
    claims = sessions.decode(token) if isinstance(token, str) else None
    if claims is None or int(claims["sub"]) != s["account_id"] or claims["sid"] != s["sid"]:
        return False
    if claims["exp"] >= s["exp"]:  # 가장 새 토큰의 인증 버전을 따른다(이메일 변경 등으로 올랐을 수 있다 — 재확인이 DB와 대조)
        s["exp"], s["ver"] = claims["exp"], claims.get("ver")
    return True


def _status(a: int, now: float, results: bool = False) -> None:
    """이 계정의 지금 처지 하나를 알린다: 진행 중인 판 > 방 > 대기열 > (다시 붙을 때만) 끊긴 사이 끝난 판 결과 > 로비."""
    if t := LOBBY.table_for(a, now):
        send(a, t.state(t.seat_of(a), []))
    elif r := LOBBY.room_of(a):  # 처지 알림은 본인에게만(방 구성이 바뀐 게 아니다)
        send(a, room_msg(r, next(i for i, m in enumerate(r.members) if m.account == a)))
    elif any(p.account == a for p in LOBBY.queue):
        tell_queued(a)
    elif results and (t := LOBBY.finished_for(a, now)):
        send(a, t.state(t.seat_of(a), []))
    else:
        send(a, {"t": "lobby"})


def _purge_expired() -> None:
    """토큰이 만료된 대기자·방 사람을 매칭·시작 전에 뺀다 — 감시 작업(_watch)이 닫기 전 틈에 판에 들어가 손패를 받지 않게.
    ponytail: 메시지마다 대기열+방 인원을 훑는다(인원에 비례). 사람이 많아지면 만료 시각 순 힙으로."""
    now = time.time()
    for a in {p.account for p in LOBBY.queue} | {m.account for r in LOBBY.rooms.values() for m in r.members}:
        w = CONNS.get(a)
        if w is not None and (s := SESS.get(w)) and now >= s["exp"]:
            _drop(a, w, 4401)


def _handle(a: int, me: Player, m: dict) -> None:
    now, kind = clock(), m.get("t")
    if kind == "ping":
        send(a, {"t": "pong"})
    elif kind == "queue":
        if t := LOBBY.enqueue(me, now):
            push(t, [])
        else:
            tell_queued(a)  # 들어간 사람에게는 바로
        push_queue()  # 다른 대기자에게는 타이머가 모아서
    elif kind == "unqueue":
        left = LOBBY.unqueue(a)
        _status(a, now)  # 그새 매칭됐으면 lobby가 아니라 판 상태
        if left:  # 대기열에 없던 사람의 취소로 모두에게 다시 보내지 않는다
            push_queue()
    elif kind == "room.create":
        push_room(LOBBY.create_room(me, now))
    elif kind == "room.join":
        code = m.get("code")
        if not isinstance(code, str) or len(code) > 12:
            raise LobbyError("no_room")
        push_room(LOBBY.join_room(me, code, now))
    elif kind == "room.leave":
        r = LOBBY.leave_room(a)
        _status(a, now)  # 그새 방장이 시작했으면 판 상태
        if r:
            push_room(r)
    elif kind == "room.start":
        push(LOBBY.start_room(a, now), [])
    elif kind == "move":
        t, tiles, ply = LOBBY.table_for(a, now), m.get("tiles"), m.get("ply")
        if t is None or m.get("game") != t.id:
            raise LobbyError("no_game")
        if type(ply) is not int:  # 늦게 온 옛 수를 가리려면 번호가 꼭 있어야 한다
            raise Illegal("bad_ply")
        if not isinstance(tiles, list) or len(tiles) > 5 or not all(isinstance(x, str) for x in tiles):
            raise Illegal("bad_tile")
        push(t, t.move(a, tiles, now, ply))
    else:
        raise LobbyError("unknown")


@router.websocket("/api/ws")
async def ws_endpoint(ws: WebSocket):
    origin = ws.headers.get("origin")
    if origin is not None and origin != web.origin():  # 다른 사이트 페이지가 사용자 쿠키로 붙는 것 차단
        await ws.close(4403)
        return
    ip = web.client_ip(ws)
    if sum(PENDING.values()) >= PENDING_MAX or PENDING.get(ip, 0) >= PENDING_PER_IP:  # 인증 안 한 연결로 소켓·메모리를 채우는 것 차단
        # 업그레이드 전에 거절한다(uvicorn에서는 HTTP 403). 받고 1013으로 닫으면 구분은 되지만 그 소켓 자체가
        # 한도 밖에서 쌓일 수 있다 — 막는 쪽을 골랐다. 앱은 어느 쪽이든 재연결 간격을 늘려 다시 붙는다.
        await ws.close(1013)
        return
    PENDING[ip] = PENDING.get(ip, 0) + 1
    try:
        await ws.accept()
        try:
            s = await asyncio.wait_for(_authenticate(ws, origin is not None), AUTH_WAIT)  # DB 대기까지 포함해 5초
        except Exception:  # 시간 초과·끊김
            s = None
        if s is None or time.time() >= s["exp"]:  # DB 조회를 기다리는 사이 만료됐으면 등록 전에 거절
            await _close(ws, 4401)  # 닫힘이 끝날 때까지 '인증 중'으로 센다(상대가 늦게 답해도 한도를 못 넘게)
            return
    finally:
        PENDING[ip] -= 1
        if not PENDING[ip]:
            del PENDING[ip]
    a = s["account_id"]
    # 기기는 앱이 보내는 머리글만 쓴다 — 브라우저는 소켓에 머리글을 못 달고, User-Agent는 남남끼리도 같다.
    # 한계: 머리글은 클라이언트가 정하는 값이라 빼거나 바꾸면 통과한다. 같은 사람 거르기의 기준은 IP이고 기기는 보조(ADR-0023).
    me = Player(a, s["nickname"], ip, ws.headers.get("x-kumoniji-device", "")[:200])
    q: asyncio.Queue = asyncio.Queue()
    OUT[ws] = q
    SESS[ws] = s
    writer = asyncio.create_task(_writer(a, ws, q))
    old = CONNS.get(a)
    CONNS[a] = ws  # 먼저 바꿔 둬야 옛 연결을 닫을 때 대기열·판 자리를 건드리지 않는다
    if old is not None:
        _drop(a, old, 4409)
    now = clock()
    _purge_expired()
    if LOBBY.update(me, now):  # 대기 중 다시 붙음 → 새 IP·기기로 다시 매칭(되면 아래에서 판 상태를 보낸다)
        push_queue()
    if t := LOBBY.table_for(a, now):  # 다시 붙음(또는 방금 매칭) → 모두에게 끊김 표시가 풀린 판 상태
        t.set_connected(a, True, now)
        push(t, [])
    else:
        _status(a, now, results=True)

    mono = time.monotonic
    last = mono()
    recent: deque[float] = deque()
    watcher = asyncio.create_task(_watch(ws, s))

    async def end(code: int) -> None:  # 닫기로 정한 순간 대기열·방에서 뺀다(닫힘 전송을 기다리는 사이 매칭에 끼지 않게)
        _leave(a, ws)
        await _close(ws, code)

    try:
        while True:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), max(IDLE - (mono() - last), 0.01))
            except TimeoutError:
                await end(4408)
                break
            except KeyError:  # 바이너리 프레임(receive_text가 'text'를 못 찾음) — 텍스트 JSON만 받는다
                await end(1003)
                break
            if CONNS.get(a) is not ws or ws not in OUT:  # 새 연결에 밀렸거나 보내기가 막혀·세션이 끝나 닫는 중
                break
            last = mono()
            recent.append(last)
            while recent and last - recent[0] > 1:
                recent.popleft()
            if len(raw.encode()) > MAX_BYTES or len(recent) > RATE:
                await end(1009 if len(raw.encode()) > MAX_BYTES else 1008)
                break
            try:
                m = json.loads(raw)
                if not isinstance(m, dict):
                    raise ValueError
            except (ValueError, RecursionError):  # JSON 아님, 또는 중첩이 너무 깊음(3.13은 2KB 안에서 JSONDecodeError지만 버전 따라 다름)
                send(a, {"t": "error", "code": "bad_message"})
                continue
            if m.get("t") == "auth":  # 연결 중 토큰 갱신
                if not _renew(s, m.get("token")):
                    send(a, {"t": "error", "code": "auth"})
                continue
            if time.time() >= s["exp"]:  # 만료된 토큰으로는 아무것도 못 한다(닫기는 _watch가 곧 한다)
                send(a, {"t": "error", "code": "auth"})
                continue
            _purge_expired()  # 매칭·시작 전에 만료된 대기자·방 사람을 뺀다 — 그사이 내가 만료돼 빠졌으면 처리하지 않는다
            if CONNS.get(a) is not ws:
                break
            try:
                _handle(a, me, m)
            except LobbyError as e:
                send(a, {"t": "error", "code": e.code})
            except NotYourTurn:
                send(a, {"t": "error", "code": "not_your_turn"})
            except Illegal as e:
                send(a, {"t": "error", "code": "illegal", "reason": e.code})
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        watcher.cancel()
        writer.cancel()
        _leave(a, ws)
