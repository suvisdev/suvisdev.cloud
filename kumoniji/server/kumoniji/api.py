"""쿠모니지 API: 사람(0번) 1명 + 봇 3명(난이도는 판마다 고름). 판은 메모리에만 둔다.
로그인한(인증된) 계정만 판을 만들고, 판은 만든 계정만 볼 수 있다(ADR-0017). 계정 API는 accounts/web.py."""

import asyncio
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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .accounts import db, limits, service, sessions
from .accounts.web import player
from .accounts.web import router as auth_router
from .bots import can_beat, pick, seen
from .game import Game, IllegalMove
from .multi import ws as multi_ws
from .view import dec, enc, reason, view

Level = Literal["easy", "normal", "hard"]

HUMAN, MAX_GAMES = 0, 2000
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


GAMES: OrderedDict[str, Room] = OrderedDict()
LOCK = threading.Lock()  # GAMES·CREATES(사전) 전용 — 판 진행은 Room.lock
CREATES: defaultdict[str, deque[float]] = defaultdict(deque)
log = logging.getLogger("kumoniji")


def _sweep_accounts() -> None:
    with db.tx() as c:
        service.purge_unverified(c)
        service.purge_deleted(c)
        limits.sweep(c)
        sessions.sweep(c)


async def _housekeeping():
    """미인증 가입(24시간)·탈퇴 재적용·오래된 시도 기록 정리. 시작 때 한 번, 그 뒤 1시간마다.
    DB 작업은 스레드에서 — 이벤트 루프에서 기다리면 멀티의 소켓 수신·20초 타이머가 같이 멈춘다."""
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


class Move(BaseModel):
    tiles: list[str] = Field(max_length=5)


class NewGame(BaseModel):
    level: Level = "normal"


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
    level = (body or NewGame()).level
    with LOCK:
        if not allow_create(str(me["account_id"])):
            raise HTTPException(429, "잠시 후 다시 시도")
    rng = random.Random(secrets.randbits(64))
    g, gid, events = Game.deal(rng), secrets.token_urlsafe(12), []
    run_bots(g, rng, events, level)
    with LOCK:
        GAMES[gid] = Room(g, rng, level, me["account_id"])
        while len(GAMES) > MAX_GAMES:
            GAMES.popitem(last=False)
    return view(gid, g, events, level)


@app.get("/api/games/{gid}")
def get_game(gid: str, me: dict = Depends(player)):
    with LOCK:
        room = load(gid, me["account_id"])
    with room.lock:
        return view(gid, room.game, [], room.level)


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
        return view(gid, g, events, room.level)


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
