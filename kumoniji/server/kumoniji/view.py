"""판 상태를 자리별로 직렬화(싱글 api·멀티 공용). 타일 표기는 무늬 글자 + 숫자(예: s3, c13)."""

from fastapi import HTTPException

from .bots import plays
from .game import Game
from .rules import SHAPES, beats, classify, value

SUIT = {"산": "m", "벚": "s", "잎": "l", "솜": "c"}
CODE = {v: k for k, v in SUIT.items()}
HUMAN = 0  # 싱글에서 사람 자리


def enc(t):
    return f"{SUIT[t[0]]}{t[1]}"


def dec(s: str):
    # 예전과 같은 표기를 받되, int()가 실패하는 입력('²'는 isdigit이지만 숫자가 아님, 4300자리 넘는 숫자는 int 한도)은 500이 아니라 422로
    num = s[1:]
    if len(s) < 2 or s[0] not in CODE or not num.isdigit():
        raise HTTPException(422, "잘못된 타일 표기")
    try:
        n = int(num)
    except ValueError:
        raise HTTPException(422, "잘못된 타일 표기") from None
    if not 1 <= n <= 13:
        raise HTTPException(422, "잘못된 타일 표기")
    return (CODE[s[0]], n)


def legal_moves(g: Game, seat: int = HUMAN) -> list[list[str]]:
    """그 자리 차례일 때 지금 낼 수 있는 조합 전부(앱은 고른 패가 이 중 하나와 같을 때만 '내기'를 켠다). 판정은 서버 규칙 그대로."""
    if g.winner is not None or g.turn != seat:
        return []
    return [[enc(t) for t in p] for p in plays(g.hands[seat]) if beats(g.table, p)]


def reason(g: Game, tiles: list, seat: int = HUMAN) -> str:
    """낼 수 없는 이유(앱이 언어별 문구로 바꿈)."""
    if any(t not in g.hands[seat] for t in tiles):
        return "not_in_hand"
    if classify(tiles) is None:
        return "not_combo"
    if g.table and len(tiles) != len(g.table):
        return "count"
    if len(tiles) <= 3 and g.table and tiles[0][1] == g.table[0][1]:
        return "suit"
    return "weaker"


def seat_plays(g: Game) -> list[list[str] | None]:
    """이번 바퀴의 최근 세 수만, 자리마다 마지막으로 낸 패(안 냈으면 None). 앱이 각 자리 앞에 놓는다.
    네 번째 전 수(보통 내 차례에 보이던 내 첫 패)는 지운다(11-21 사용자 결정)."""
    out: list[list[str] | None] = [None] * 4
    for seat, m in [*g.history, *([(g.last, g.table)] if g.table else [])][-3:]:
        out[seat] = [enc(t) for t in m]
    return out


def view(gid: str, g: Game, events: list, level: str = "normal", seat: int = HUMAN) -> dict:
    """seat 자리가 볼 수 있는 상태 — 손패·낼 수 있는 조합은 그 자리 것만, 남의 손패는 장수만(멀티도 같은 함수)."""
    return {
        "id": gid,
        "level": level,
        "today": SUIT[g.today],
        "turn": g.turn,
        "hand": [enc(t) for t in sorted(g.hands[seat], key=value)],
        "counts": [len(h) for h in g.hands],
        "table": [enc(t) for t in g.table],
        "last": g.last,
        # 마지막으로 낸 사람 뒤로 이어서 패스한 자리(바퀴가 넘어가면 비어 있음)
        "passed": []
        if g.last is None
        else [(g.last + k) % 4 for k in range(1, g.passes + 1)],
        "plays": seat_plays(g),
        "petals": [len(p) for p in g.petals],
        "bonus": list(g.bonus),  # 복사 — 만든 뒤 판이 진행돼도 이 상태는 그 시점 값
        "doubles": g.doubles,
        "winner": g.winner,
        "settlement": g.settlement(),
        "events": events,
        "moves": (moves := legal_moves(g, seat)),
        "playable": sorted({t for m in moves for t in m}, key=lambda c: value(dec(c))),
        "suits": [SUIT[x] for x in reversed(SHAPES)],  # 센 것 → 약한 것
    }


