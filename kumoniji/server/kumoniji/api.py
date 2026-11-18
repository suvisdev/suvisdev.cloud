"""쿠모니지 1단계 API: 사람(0번) 1명 + 봇 3명. 판은 메모리에만 둔다."""

import random
import secrets
import threading
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .bots import pick
from .game import Game, IllegalMove
from .rules import value

SUIT = {"산": "m", "벚": "s", "잎": "l", "솜": "c"}
CODE = {v: k for k, v in SUIT.items()}
HUMAN, MAX_GAMES = 0, 2000
# ponytail: 메모리 보관·재시작 시 사라짐·replicas 1 고정. 계정 단계(3단계)에서 DB로 옮긴다.
GAMES: OrderedDict[str, tuple[Game, random.Random]] = OrderedDict()
# 동기 핸들러는 스레드에서 돌아 같은 판 요청이 겹칠 수 있다 → 판 상태를 읽고 바꾸는 구간 전체를 한 잠금으로 직렬화.
# ponytail: 전역 잠금 하나(한 수 처리는 수 ms). 동시 접속이 늘어 대기가 보이면 판별 잠금으로.
LOCK = threading.Lock()
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


def view(gid: str, g: Game, events: list) -> dict:
    return {
        "id": gid,
        "today": SUIT[g.today],
        "turn": g.turn,
        "hand": [enc(t) for t in sorted(g.hands[HUMAN], key=value)],
        "counts": [len(h) for h in g.hands],
        "table": [enc(t) for t in g.table],
        "last": g.last,
        "petals": [len(p) for p in g.petals],
        "bonus": g.bonus,
        "doubles": g.doubles,
        "winner": g.winner,
        "settlement": g.settlement(),
        "events": events,
    }


def load(gid: str) -> tuple[Game, random.Random]:
    if gid not in GAMES:
        raise HTTPException(404, "없는 판")
    return GAMES[gid]


@app.post("/api/games")
def new_game():
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
        except IllegalMove as e:
            raise HTTPException(422, str(e)) from None
        events = [{"seat": HUMAN, "tiles": [enc(t) for t in tiles] or None}]
        run_bots(g, rng, events)
        return view(gid, g, events)


WEB = Path(__file__).resolve().parent.parent / "web"
if WEB.is_dir():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
