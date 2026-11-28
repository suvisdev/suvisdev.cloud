"""쿠모니지 API: 사람(0번) 1명 + 봇 3명(난이도는 판마다 고름). 판은 메모리에만 둔다.
로그인한(인증된) 계정만 판을 만들고, 판은 만든 계정만 볼 수 있다(ADR-0017). 계정 API는 accounts/web.py."""

import asyncio
import itertools
import logging
import os
import random
import secrets
import threading
import time
from contextlib import asynccontextmanager
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .accounts import db, limits, service, sessions
from .accounts.web import player
from .accounts.web import router as auth_router
from .bots import can_beat, pick, seen
from .game import Game, IllegalMove
from .multi import ws as multi_ws
from .view import dec, enc, reason, view
from .wallet import store
from .wallet import web as wallet_web

Level = Literal["easy", "normal", "hard"]

HUMAN, MAX_GAMES = 0, 2000
RECORD_RETRY = (2, 10, 60)  # 판 끝 기록 실패 시 다시 시도할 간격(초), 끝 값으로 성공할 때까지
CREATE_PER_MIN = 30  # 계정 하나가 1분에 만들 수 있는 판 — 판을 마구 만들어 남의 진행 중인 판을 밀어내지 못하게
# ponytail: 메모리 보관·재시작 시 사라짐·replicas 1 고정. 계정 단계(3단계)에서 DB로 옮긴다.


@dataclass
class Room:
    game: Game
    rng: random.Random
    level: str = "normal"
    account_id: int = 0  # 만든 계정 — 다른 계정은 이 판을 못 본다(404)
    # 동기 핸들러는 스레드에서 돌아 같은 판 요청이 겹칠 수 있다 → 판 상태를 읽고 바꾸는 구간 전체를 판별 잠금으로 직렬화.
    # 판별인 이유: hard 봇은 한 수에 최대 0.5초라 전역 잠금이면 남의 판까지 멈춘다.
    lock: threading.Lock = field(default_factory=threading.Lock)
    recorded: bool = False  # 판 끝 기록(미션·지갑)을 마쳤나 — 실패하면 다음 요청에서 다시
    ended: float | None = None  # 판이 끝난 걸 처음 본 시각 — 재시도가 자정을 넘겨도 미션은 그날 몫


GAMES: OrderedDict[str, Room] = OrderedDict()
LOCK = threading.Lock()  # GAMES·CREATES(사전) 전용 — 판 진행은 Room.lock
CREATES: defaultdict[str, deque[float]] = defaultdict(deque)
RIDS: OrderedDict[tuple[int, str], str | None] = OrderedDict()  # (계정, 요청 id) → 만든 판 id(만드는 중이면 None)
MAX_RIDS = 20_000  # 판이 GAMES에서 밀려나도 기록은 남긴다 — 같은 rid가 다시 오면 하트를 다시 쓰지 않고 410
UNKNOWN = ""  # RIDS 값: 앞선 요청이 DB 오류로 끝나 하트가 커밋됐는지 모름 — 같은 rid가 오면 원장으로 확인(판 id는 비지 않는다)
log = logging.getLogger("kumoniji")


def _sweep_accounts() -> None:
    # 정리마다 트랜잭션을 따로 — 한 트랜잭션에서 시도 기록·세션을 차례로 잠그면, 세션을 먼저 잠그고 시도 기록을 지우는
    # 탈퇴와 엇갈려 교착할 수 있다(리뷰 9차)
    # 한 정리가 실패해도(잠금 오류 등) 나머지는 돈다 — 세션 정리가 밀려 방침의 보관 기간을 넘기지 않게(리뷰)
    for step in (service.purge_unverified, service.purge_deleted, limits.sweep, sessions.sweep):
        try:
            with db.tx() as c:
                step(c)
        except Exception:
            log.exception("계정 정리 실패: %s", step.__name__)


async def _housekeeping():
    """미인증 가입(24시간)·탈퇴 재적용·오래된 시도 기록 정리. 시작 때 한 번, 그 뒤 1시간마다.
    DB 작업은 스레드에서 — 이벤트 루프에서 기다리면 멀티의 소켓 수신·차례 타이머가 같이 멈춘다."""
    while True:
        try:
            await asyncio.to_thread(_sweep_accounts)
        except Exception:
            log.exception("계정 정리 작업 실패")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(_app):
    url = os.environ.get("KUMONIJI_DATABASE_URL")
    task = None
    if url:  # 테스트는 픽스처가 직접 db.init을 부른다
        db.init(url)
        task = asyncio.create_task(_housekeeping())
    ticker = asyncio.create_task(multi_ws.tick_forever())
    yield
    ticker.cancel()
    if task:
        task.cancel()
    db.close()


app = FastAPI(
    title="kumoniji", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
)
app.include_router(auth_router)
app.include_router(multi_ws.router)
app.include_router(wallet_web.router)


class Move(BaseModel):
    tiles: list[str] = Field(max_length=5)


class NewGame(BaseModel):
    level: Level = "normal"
    rid: str | None = Field(None, min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")  # 다시 보내기용 요청 id(앱이 판마다 새로 만든다)


def run_bots(g: Game, rng: random.Random, events: list, level: str = "normal"):
    """사람 차례가 올 때까지 봇을 돌린다.
    아직 안 나온 패(모든 손패) 전체로도 바닥을 이길 수 없으면(예: 산13) 남은 자리 모두를 한 번에 패스시킨다
    (auto 표시 — 앱이 한 명씩이 아니라 한꺼번에 보여 준다, 11-25 사용자). 사람 손패만 보고 넘기면 남들이
    '저 사람은 이길 패가 없다'를 알게 되므로 공개된 정보로만 판단한다. 패스는 바닥을 안 바꾸니 한 바퀴에 한 번만 본다."""
    checked = None  # 이 바닥으로 이미 '누군가 이길 수 있음'을 확인했으면 다시 안 본다
    while g.winner is None:
        if g.table and g.table is not checked:
            if not can_beat(g.table, [t for h in g.hands for t in h]):
                while g.table:  # 남은 자리 모두 패스 → 바퀴가 끝나 바닥이 빈다
                    events.append({"seat": g.turn, "tiles": None, "auto": True})
                    g.play(g.turn, None)
                continue
            checked = g.table
        seat = g.turn
        if seat == HUMAN:
            return
        m = pick(level, seen(g, seat), rng)
        g.play(seat, m)
        events.append({"seat": seat, "tiles": [enc(t) for t in m] if m else None})


def use_heart(account_id: int, rid: str | None = None, resume: bool = False) -> None:
    """싱글은 판을 열 때 하트 1개(멀티는 판이 잡힐 때, multi/ws.py).
    rid가 있으면 원장 참조로 남긴다 — 서버가 재시작돼 메모리의 RIDS가 사라져도 같은 요청으로 두 번 쓰지 않는다(410).
    resume: 앞선 같은 요청이 DB 오류로 끝나 커밋됐는지 모르는 경우 — 원장에 있으면 이미 낸 것으로 보고 판을 연다."""
    ref = f"new:{rid}" if rid else None
    checked = False
    try:
        with db.tx() as c:
            # 지갑 행 잠금을 먼저 — 같은 rid의 앞선 요청이 아직 커밋 중이면 끝날 때까지 기다린 뒤 원장을 봐야 그 하트를 본다(리뷰 지적)
            store.snapshot(c, account_id, time.time())
            if ref and c.execute(
                "SELECT 1 FROM ledger WHERE account_id = %s AND kind = 'heart' AND ref = %s", (account_id, ref)
            ).fetchone():
                if resume:
                    return
                raise HTTPException(410, "gone")  # 이미 하트를 쓰고 만든 판(응답 유실 뒤 재시작) — 앱은 새 rid로
            checked = True  # 이 rid로 낸 하트가 없음을 확인함 — 이 뒤로 원장에 생기는 행은 이 요청 것이다
            if not store.use_heart(c, account_id, time.time(), ref):
                # 옛 앱은 402를 일반 오류로 보인다 — 받아들임: 휴대폰 앱은 아직 출시 전(웹 → 안드로이드 순, SPEC)이라 설치본이 없고,
                # 웹은 이 서버와 같은 배포에서 새 앱(Task 6, 하트·충전 시각 안내)으로 바뀐다. 그래서 서버만 먼저 배포하지 않는다.
                raise HTTPException(402, {"code": "no_heart"})
    except HTTPException:
        raise
    except Exception as e:
        if checked or resume:  # 쓰는 중·커밋 중 오류, 또는 '모름'을 확인하다 실패 — 여전히 커밋됐는지 모른다(리뷰 지적)
            raise HeartUnknown from e
        raise


class HeartUnknown(Exception):
    """하트 쓰기가 커밋됐는지 모르는 DB 오류. 같은 rid의 다음 요청이 원장으로 확인한다(new_game)."""


def record(gid: str, room: Room, out: dict) -> dict:
    """판이 끝났으면 한 번만 미션·지갑에 기록하고 응답에 wallet을 붙인다(판돈은 자동 매칭만이라 싱글은 없음).
    DB가 실패해도 결과 화면은 그대로 — 스레드가 성공할 때까지 다시 시도하고, 같은 판은 원장이 두 번 넣지 않는다."""
    if room.game.winner is None:
        return out
    room.ended = room.ended or time.time()
    try:
        if room.recorded:  # 다시 읽은 결과(응답 유실·재시도 성공 뒤)에도 지금 지갑을
            with db.tx() as c:
                out["wallet"] = store.snapshot(c, room.account_id, time.time())
        else:
            out["wallet"], room.recorded = _write_record(gid, room), True  # 커밋 뒤에만 — 실패한 잔고를 안 보이게
    except store.AccountGone:  # 그사이 탈퇴 — 다시 해도 안 되니 재시도에 넣지 않는다(401)
        raise
    except Exception:
        log.exception("판 끝 기록 실패")
        if not room.recorded:
            _queue_retry(gid, room)
    return out


def _write_record(gid: str, room: Room) -> dict:
    players = store.players_of(room.game, [room.account_id if i == HUMAN else None for i in range(4)])
    with db.tx() as c:
        store.finish_game(c, f"single:{gid}", players, time.time(), stake=False, day_at=room.ended)
        return store.snapshot(c, room.account_id, time.time())


RETRY: dict[str, Room] = {}  # 기록을 다시 시도할 판 — 재시도 스레드는 하나뿐(DB 장애 때 판마다 스레드가 쌓이지 않게)
RETRY_LOCK = threading.Lock()
_retry_thread: threading.Thread | None = None


def _queue_retry(gid: str, room: Room) -> None:
    global _retry_thread
    with RETRY_LOCK:
        RETRY[gid] = room
        if _retry_thread is None:
            _retry_thread = threading.Thread(target=_retry_records, daemon=True)
            _retry_thread.start()


def _retry_records() -> None:
    """목록이 빌 때까지 RECORD_RETRY 간격으로 다시 기록한다.
    ponytail: 재시도는 메모리에만 — 그사이 서버가 재시작되면 그 판 기록은 사라진다(판 자체도 메모리)."""
    global _retry_thread
    for wait in itertools.chain(RECORD_RETRY, itertools.repeat(RECORD_RETRY[-1])):
        time.sleep(wait)
        with RETRY_LOCK:
            pending = list(RETRY.items())
        for gid, room in pending:
            if not room.recorded:
                try:
                    _write_record(gid, room)
                    room.recorded = True
                except store.AccountGone:  # 그사이 탈퇴 — 기록할 것이 없다. 남겨 두면 영영 다시 시도한다(리뷰 지적)
                    room.recorded = True
                except Exception:
                    log.exception("판 끝 기록 재시도 실패")
                    continue
            with RETRY_LOCK:
                RETRY.pop(gid, None)
        with RETRY_LOCK:
            if not RETRY:  # 비었을 때만 끝낸다 — 잠금 안에서 정하므로 그사이 들어온 판을 놓치지 않는다
                _retry_thread = None
                return


def load(gid: str, account_id: int) -> Room:
    if gid not in GAMES or GAMES[gid].account_id != account_id:
        raise HTTPException(404, "없는 판")
    # 최근에 쓴 판을 뒤로 → 꽉 차면 가장 오래 안 쓴 판부터 지운다
    GAMES.move_to_end(gid)
    return GAMES[gid]


def allow_create(key: str) -> bool:
    now, q = time.monotonic(), CREATES[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= CREATE_PER_MIN:
        return False
    q.append(now)
    if len(CREATES) > 10 * MAX_GAMES:  # 오래된 IP 기록이 끝없이 쌓이지 않게
        CREATES.clear()
    return True


@app.post("/api/games")
def new_game(body: NewGame | None = None, me: dict = Depends(player)):
    """같은 rid로 다시 오면(응답 유실 뒤 재요청) 하트를 다시 쓰지 않고 그 판을 돌려준다."""
    body, a = body or NewGame(), me["account_id"]
    key = (a, body.rid) if body.rid else None
    with LOCK:
        resume = False
        if key in RIDS:
            if (gid := RIDS[key]) is None:
                raise HTTPException(409, "creating")  # 같은 요청이 아직 만드는 중
            if gid == UNKNOWN:  # 앞선 같은 요청이 DB 오류로 끝남 — 커밋됐으면 하트는 이미 냈다(원장으로 확인)
                RIDS[key], room, resume = None, None, True
            elif (room := GAMES.get(gid)) is None:
                raise HTTPException(410, "gone")  # 만든 판이 이미 밀려남 — 앱은 새 rid로 새 판
        elif not allow_create(str(a)):
            raise HTTPException(429, "잠시 후 다시 시도")
        else:
            room = None
            if key:
                RIDS[key] = None
    if room is not None:
        with room.lock:
            return record(gid, room, view(gid, room.game, [], room.level, practice=True))
    try:
        use_heart(a, body.rid, resume)
    except HTTPException:  # 확정된 거절(402·410) — 이 rid는 잊는다
        with LOCK:
            RIDS.pop(key, None)
        raise
    except HeartUnknown:  # 커밋됐는지 모른다 — 잊으면 같은 rid가 410이 돼 하트만 잃으니 '모름'으로 남긴다(리뷰 지적)
        with LOCK:
            if key:
                RIDS[key] = UNKNOWN
        raise
    except BaseException:  # 하트를 쓰기 전 오류(원장 확인 실패 등) — 안 쓴 것이 확실하니 잊는다. '모름'으로 두면 재시작 전에
        with LOCK:  # 같은 rid로 낸 하트를 이번 것으로 착각해 공짜 판이 된다(리뷰 지적)
            RIDS.pop(key, None)
        raise
    rng = random.Random(secrets.randbits(64))
    g, gid, events = Game.deal(rng), secrets.token_urlsafe(12), []
    run_bots(g, rng, events, body.level)
    room = Room(g, rng, body.level, a)
    with LOCK:
        GAMES[gid] = room
        if key:
            RIDS[key] = gid
            # 오래된 것부터 지우되 끝난 것(판 id)만 — '모름'·만드는 중(None)이 밀려나면 같은 rid가 410이 돼 낸 하트로 판을 못
            # 연다(리뷰 지적). 둘은 DB 오류·동시 요청 때만 잠깐 있어 적다.
            stale = (k for k, v in RIDS.items() if v)
            for k in list(itertools.islice(stale, max(len(RIDS) - MAX_RIDS, 0))):
                del RIDS[k]
        while len(GAMES) > MAX_GAMES:
            GAMES.popitem(last=False)
    with room.lock:
        return record(gid, room, view(gid, g, events, body.level, practice=True))


@app.get("/api/games/{gid}")
def get_game(gid: str, me: dict = Depends(player)):
    with LOCK:
        room = load(gid, me["account_id"])
    with room.lock:
        return record(gid, room, view(gid, room.game, [], room.level, practice=True))


@app.post("/api/games/{gid}/moves")
def move(gid: str, body: Move, me: dict = Depends(player)):
    tiles = [dec(t) for t in body.tiles]
    with LOCK:
        room = load(gid, me["account_id"])
    with room.lock:
        g = room.game
        if g.winner is not None or g.turn != HUMAN:
            raise HTTPException(409, "차례가 아님")
        try:
            g.play(HUMAN, tiles or None)
        except IllegalMove:
            raise HTTPException(422, {"code": reason(g, tiles)}) from None
        events = [{"seat": HUMAN, "tiles": [enc(t) for t in tiles] or None}]
        run_bots(g, room.rng, events, room.level)
        return record(gid, room, view(gid, g, events, room.level, practice=True))


# SECURITY.md 검증 25·27. Flutter 웹 빌드가 실제로 쓰는 출처만 연다:
# CanvasKit은 자체 호스팅(deploy.sh --no-web-resources-cdn, WebAssembly → 'wasm-unsafe-eval'),
# 글꼴만 fonts.gstatic.com(앱이 글꼴을 번들하지 않음 — fetch라 페이지 주소를 읽지 못하고, Referer도 안 보낸다).
# Turnstile(challenges.cloudflare.com)은 로그인 실패가 많은 IP에만 뜨는 사람 확인.
# 예외: style-src 'unsafe-inline' — Flutter 엔진이 <style>을 직접 넣는다. 스크립트는 인라인 금지라 XSS 영향은 작다.
#       제거 기한: 글꼴을 자체 호스팅할 때 함께 다시 본다.
CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' 'wasm-unsafe-eval' https://challenges.cloudflare.com",
        "connect-src 'self' https://fonts.gstatic.com",
        "frame-src https://challenges.cloudflare.com",
        "font-src 'self' https://fonts.gstatic.com",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "worker-src 'self' blob:",
        "object-src 'none'",
        "base-uri 'self'",  # Flutter index.html의 <base href="/">
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000",
}


@app.exception_handler(store.AccountGone)
def _account_gone(_: Request, __: store.AccountGone) -> JSONResponse:
    """인증을 통과한 직후 탈퇴가 커밋된 요청 — 세션은 이미 끊겼으니 로그인 안 됨으로 답한다."""
    return JSONResponse({"detail": "auth"}, status_code=401)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """API(인증·개인정보)는 no-store. 웹 파일(main.dart.js 등)은 이름이 배포마다 같다 → 캐시 규칙이 없으면
    Cloudflare·브라우저가 옛 앱을 몇 시간씩 내준다(11-19 배포 후 실측). 매번 새 버전인지 확인하게 한다(304라 가볍다)."""
    response = await call_next(request)
    response.headers.update(HEADERS)
    response.headers["Cache-Control"] = (
        "no-store" if request.url.path.startswith("/api/") else "no-cache"
    )
    return response


WEB = Path(__file__).resolve().parent.parent / "web"


# 메일 링크(가입 인증·재설정·주소 확인·보호·비밀번호 찾기)는 앱 화면이 연다. GET은 화면만 보여 주고, 토큰은 앱이 POST로 소비한다.
def link_page():
    if not (WEB / "index.html").is_file():
        raise HTTPException(404)
    return FileResponse(WEB / "index.html")


for _page in ("verify", "reset", "email", "protect", "forgot"):
    app.add_api_route(f"/{_page}", link_page, methods=["GET"], include_in_schema=False)


if WEB.is_dir():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
