"""쿠모니지 1단계 API: 사람(0번) 1명 + 봇 3명. 판은 메모리에만 둔다."""

import random
import secrets
import threading
import time
from collections import OrderedDict, defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .bots import pick, plays
from .game import Game, IllegalMove
from .rules import SHAPES, beats, classify, value

SUIT = {"산": "m", "벚": "s", "잎": "l", "솜": "c"}
CODE = {v: k for k, v in SUIT.items()}
HUMAN, MAX_GAMES = 0, 2000
CREATE_PER_MIN = 30  # IP 하나가 1분에 만들 수 있는 판 — 판을 마구 만들어 남의 진행 중인 판을 밀어내지 못하게
# ponytail: 메모리 보관·재시작 시 사라짐·replicas 1 고정. 계정 단계(3단계)에서 DB로 옮긴다.
GAMES: OrderedDict[str, tuple[Game, random.Random]] = OrderedDict()
# 동기 핸들러는 스레드에서 돌아 같은 판 요청이 겹칠 수 있다 → 판 상태를 읽고 바꾸는 구간 전체를 한 잠금으로 직렬화.
# ponytail: 전역 잠금 하나(한 수 처리는 수 ms). 동시 접속이 늘어 대기가 보이면 판별 잠금으로.
LOCK = threading.Lock()
CREATES: defaultdict[str, deque[float]] = defaultdict(deque)
app = FastAPI(title="kumoniji", docs_url=None, redoc_url=None, openapi_url=None)


def enc(t):
    return f"{SUIT[t[0]]}{t[1]}"


def dec(s: str):
    if (
        len(s) < 2
        or s[0] not in CODE
        or not s[1:].isdigit()
        or not 1 <= int(s[1:]) <= 13
    ):
        raise HTTPException(422, "잘못된 타일 표기")
    return (CODE[s[0]], int(s[1:]))


class Move(BaseModel):
    tiles: list[str] = Field(max_length=5)


def run_bots(g: Game, rng: random.Random, events: list):
    while g.winner is None and g.turn != HUMAN:
        seat = g.turn
        m = pick("aim", g.hands[seat], g.table, g.today, rng)
        g.play(seat, m)
        events.append({"seat": seat, "tiles": [enc(t) for t in m] if m else None})


def legal_moves(g: Game) -> list[list[str]]:
    """사람 차례일 때 지금 낼 수 있는 조합 전부(앱은 고른 패가 이 중 하나와 같을 때만 '내기'를 켠다). 판정은 서버 규칙 그대로."""
    if g.winner is not None or g.turn != HUMAN:
        return []
    return [[enc(t) for t in p] for p in plays(g.hands[HUMAN]) if beats(g.table, p)]


def reason(g: Game, tiles: list) -> str:
    """낼 수 없는 이유(앱이 언어별 문구로 바꿈)."""
    if not tiles:
        return "lead_pass"
    if any(t not in g.hands[HUMAN] for t in tiles):
        return "not_in_hand"
    if classify(tiles) is None:
        return "not_combo"
    if g.table and len(tiles) != len(g.table):
        return "count"
    if len(tiles) <= 3 and g.table and tiles[0][1] == g.table[0][1]:
        return "suit"
    return "weaker"


def seat_plays(g: Game) -> list[list[str] | None]:
    """이번 바퀴에 자리마다 마지막으로 낸 패(안 냈으면 None). 앱이 각 자리 앞에 놓는다."""
    out: list[list[str] | None] = [None] * 4
    for seat, m in [*g.history, *([(g.last, g.table)] if g.table else [])]:
        out[seat] = [enc(t) for t in m]
    return out


def view(gid: str, g: Game, events: list) -> dict:
    return {
        "id": gid,
        "today": SUIT[g.today],
        "turn": g.turn,
        "hand": [enc(t) for t in sorted(g.hands[HUMAN], key=value)],
        "counts": [len(h) for h in g.hands],
        "table": [enc(t) for t in g.table],
        "last": g.last,
        # 마지막으로 낸 사람 뒤로 이어서 패스한 자리(바퀴가 넘어가면 비어 있음)
        "passed": []
        if g.last is None
        else [(g.last + k) % 4 for k in range(1, g.passes + 1)],
        "plays": seat_plays(g),
        "petals": [len(p) for p in g.petals],
        "bonus": g.bonus,
        "doubles": g.doubles,
        "winner": g.winner,
        "settlement": g.settlement(),
        "events": events,
        "moves": (moves := legal_moves(g)),
        "playable": sorted({t for m in moves for t in m}, key=lambda c: value(dec(c))),
        "suits": [SUIT[x] for x in reversed(SHAPES)],  # 센 것 → 약한 것
    }


def load(gid: str) -> tuple[Game, random.Random]:
    if gid not in GAMES:
        raise HTTPException(404, "없는 판")
    # 최근에 쓴 판을 뒤로 → 꽉 차면 가장 오래 안 쓴 판부터 지운다
    GAMES.move_to_end(gid)
    return GAMES[gid]


def allow_create(ip: str) -> bool:
    now, q = time.monotonic(), CREATES[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= CREATE_PER_MIN:
        return False
    q.append(now)
    if len(CREATES) > 10 * MAX_GAMES:  # 오래된 IP 기록이 끝없이 쌓이지 않게
        CREATES.clear()
    return True


@app.post("/api/games")
def new_game(request: Request):
    # 터널(Cloudflare) 뒤라 실제 접속 IP는 CF-Connecting-IP. 서비스는 터널로만 들어온다.
    ip = request.headers.get("cf-connecting-ip") or (
        request.client.host if request.client else ""
    )
    with LOCK:
        if not allow_create(ip):
            raise HTTPException(429, "잠시 후 다시 시도")
    rng = random.Random(secrets.randbits(64))
    g, gid, events = Game.deal(rng), secrets.token_urlsafe(12), []
    run_bots(g, rng, events)
    with LOCK:
        GAMES[gid] = (g, rng)
        while len(GAMES) > MAX_GAMES:
            GAMES.popitem(last=False)
        return view(gid, g, events)


@app.get("/api/games/{gid}")
def get_game(gid: str):
    with LOCK:
        return view(gid, load(gid)[0], [])


@app.post("/api/games/{gid}/moves")
def move(gid: str, body: Move):
    tiles = [dec(t) for t in body.tiles]
    with LOCK:
        g, rng = load(gid)
        if g.winner is not None or g.turn != HUMAN:
            raise HTTPException(409, "차례가 아님")
        try:
            g.play(HUMAN, tiles or None)
        except IllegalMove:
            raise HTTPException(422, {"code": reason(g, tiles)}) from None
        events = [{"seat": HUMAN, "tiles": [enc(t) for t in tiles] or None}]
        run_bots(g, rng, events)
        return view(gid, g, events)


WEB = Path(__file__).resolve().parent.parent / "web"
if WEB.is_dir():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
