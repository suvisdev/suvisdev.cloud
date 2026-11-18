# 쿠모니지 1단계(봇 3명과 혼자 치기, 웹) 구현 계획

**Goal:** `kumoniji.suvisdev.cloud`에서 로그인 없이 봇 3명과 쿠모니지 한 판을 끝까지 칠 수 있게 한다.

**Architecture:** 판정은 서버가 한다(서버 권위). 이미 하네스 88개로 검증한 `제안_v4/rules.py`를 그대로 엔진으로 옮기고, 한 수씩 진행하는 `Game` 상태를 그 위에 얹는다. 앱은 Flutter 하나로 웹(1단계)·안드로이드·아이폰을 같이 만들고, 웹 빌드 결과는 FastAPI가 같은 컨테이너에서 정적 파일로 낸다(컨테이너 1개·Deployment 1개). 판은 메모리에만 둔다(1단계는 계정·DB 없음).

**Tech Stack:** Python 3.13 · FastAPI 0.136.3 · uvicorn 0.49.0 · pytest / Flutter 3.47.x(Dart ^3.12.2) · http ^1.6.0 · flutter_svg · flutter_localizations / k3s · Traefik Ingress · Cloudflare Tunnel

## Global Constraints
- 규칙은 **제안 v4로 확정**(2026-11-18 사용자 결정). 엔진은 `제안_v4/rules.py`·`cases.json`과 한 글자도 다르게 판정하지 않는다. 규칙을 바꾸면 `cases.json`부터 고친다.
- 오늘의 무늬 ×5는 **지금 규칙(누가 언제 내도 걸림)**. 사용자가 조건을 다시 고민 중이므로 `rules.py`의 `doubles` 한 줄만 고치면 바뀌게 둔다.
- 언어: 영어·일본어 우선, 한국어 포함(en / ja / ko).
- 재화·결제·로그인·멀티는 1단계에 넣지 않는다. 화면에 돈 표기 금지 — 점수는 "점/pts/点"(사행성 규제, 환전 불가).
- 그림은 Codex가 만든다(시안 F16 기준: 11 구름 · 12 무지개 · 13 해, 동·은·금 이중 테두리, 벚꽃은 ②우산콩).
- 무료 인프라만. 노트북 k3s에 올린다(노트북이 꺼지면 게임도 꺼짐).
- 서브도메인: `kumoniji.suvisdev.cloud`. Cloudflare 대시보드의 터널 공개 호스트 추가는 **사용자 작업**.

---

## 파일 구조

```text
kumoniji/
├── CLAUDE.md                     # 이 스택 규칙(짧게): 규칙은 cases.json부터, 서버 권위, 실행 명령
├── _docs/plans/                  # 이 계획
├── server/
│   ├── requirements.txt          # fastapi==0.136.3, uvicorn==0.49.0
│   ├── kumoniji/
│   │   ├── __init__.py
│   │   ├── rules.py              # 제안_v4/rules.py 그대로(판정·정산·하네스 실행기)
│   │   ├── cases.json            # 제안_v4/cases.json 그대로(88개)
│   │   ├── bots.py               # sim.py의 plays·strength·choose + sim_v4.py의 pick
│   │   ├── game.py               # 한 수씩 진행하는 Game(서버 권위 상태)
│   │   └── api.py                # FastAPI 앱: /api/games…, 웹 정적 파일
│   └── tests/
│       ├── test_rules_cases.py   # cases.json 88개 + 전수 분류
│       ├── test_game.py          # Game == rules.simulate (사례·무작위 500판)
│       └── test_api.py           # TestClient로 한 판 끝까지
├── app/                          # Flutter (web 우선)
│   ├── pubspec.yaml
│   ├── l10n.yaml, lib/l10n/app_{en,ja,ko}.arb
│   ├── assets/tiles/{m,s,l,c}{1..13}.svg, back.svg
│   ├── lib/main.dart             # MaterialApp + 언어
│   ├── lib/api.dart              # GameState 모델 + HTTP
│   ├── lib/tile.dart             # 패 위젯
│   ├── lib/table_screen.dart     # 게임 화면
│   └── test/{api_test,tile_test}.dart
├── Dockerfile                    # Flutter web 빌드 → python 이미지에 복사
└── deploy.sh                     # 빌드 → k3s import → apply → rollout
k8s/kumoniji.yaml                 # Deployment·Service·Ingress(host kumoniji.suvisdev.cloud)
.github/workflows/kumoniji-ci.yml # pytest + flutter analyze/test
```

타일 표기(API·앱): 무늬 코드 한 글자 + 숫자. `m`=산, `s`=벚꽃, `l`=잎사귀, `c`=솜사탕. 예: `s3`, `c13`. 엔진 안은 기존 한글 표기(`("벚", 3)`) 그대로 두고 API 경계에서만 바꾼다.

---

### Task 1: 엔진 옮기기 + 하네스를 pytest로

**Files:**
- Create: `kumoniji/CLAUDE.md`, `kumoniji/server/requirements.txt`, `kumoniji/server/kumoniji/__init__.py`(빈 파일)
- Create(복사): `kumoniji/server/kumoniji/rules.py` ← `scratchpad/rules-harness/제안_v4/rules.py`, `cases.json` ← 같은 폴더
- Test: `kumoniji/server/tests/test_rules_cases.py`
- Modify: 루트 `CLAUDE.md` 저장소 구조 표에 `kumoniji/` 한 줄

**Interfaces:**
- Produces: `rules.run_case(case) -> object`, `rules.simulate(hands, moves, today) -> dict`, `rules.settle(hands_left, petals, bonus, doubles) -> list[int]`, `rules.beats`, `rules.classify`, `rules.first_player`, `rules.special_steps(move, today, finish) -> int`, `rules.small_today(move, today) -> int`, `rules.value`, `rules.DECK`, `rules.SHAPES`, `rules.full_count()`

- [ ] **Step 1: 테스트 작성**

```python
# kumoniji/server/tests/test_rules_cases.py
import json
from pathlib import Path

import pytest

from kumoniji import rules

CASES = json.loads((Path(rules.__file__).parent / "cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case(case):
    assert rules.run_case(case) == case["expect"]


def test_case_count():
    assert len(CASES) == 88


def test_full_count():
    got = rules.full_count()
    assert (got["포카드"], got["스트레이트플러시"], got["같은모양홀짝"]) == (624, 36, 20)
```

- [ ] **Step 2: 실패 확인** — `cd kumoniji/server && uv run --no-project --with pytest pytest -q` → `ModuleNotFoundError: kumoniji.rules`
- [ ] **Step 3: 복사** — rules.py·cases.json을 그대로 복사. rules.py 맨 아래 `__main__`의 `Path(__file__).parent / "cases.json"`은 같은 폴더라 그대로 동작. requirements.txt:

```text
fastapi==0.136.3
uvicorn==0.49.0
```

- [ ] **Step 4: 통과 확인** — 같은 명령 → `90 passed`. 그리고 `diff` 로 원본과 바이트 동일 확인.
- [ ] **Step 5: 커밋** — `feat: 쿠모니지 규칙 엔진과 하네스 추가`

---

### Task 2: 한 수씩 진행하는 Game

**Files:**
- Create: `kumoniji/server/kumoniji/game.py`
- Test: `kumoniji/server/tests/test_game.py`

**Interfaces:**
- Consumes: Task 1의 rules 함수들
- Produces: `Tile = tuple[str, int]`, `class IllegalMove(ValueError)`, `@dataclass Game(hands, today, turn, table, last, passes, petals, bonus, pot, doubles, winner)`, `Game.deal(rng) -> Game`, `Game.play(seat: int, move: list[Tile] | None) -> None`(None=패스, 어기면 IllegalMove), `Game.settlement() -> list[int] | None`

- [ ] **Step 1: 테스트 작성** — 하네스의 simulate 사례를 Game으로 다시 돌려 결과가 같은지 본다.

```python
# kumoniji/server/tests/test_game.py
import json
from pathlib import Path

import pytest

from kumoniji import rules
from kumoniji.game import Game, IllegalMove

CASES = [c for c in json.loads((Path(rules.__file__).parent / "cases.json").read_text()) if c["type"] == "simulate"]
P = rules.parse


def replay(hands, moves, today):
    g = Game(hands=[list(h) for h in hands], today=today, turn=rules.first_player(hands))
    for i, m in enumerate(moves):
        try:
            g.play(g.turn, m)
        except IllegalMove:
            return g, i
    return g, None


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_matches_simulate_cases(case):
    hands = [[P(t) for t in h] for h in case["hands"]]
    moves = [None if m == "패스" else [P(t) for t in m] for m in case["moves"]]
    g, err = replay(hands, moves, case["today"])
    got = dict(error_at=err, winner=g.winner, petals=g.petals, bonus=g.bonus, doubles=g.doubles, hands=g.hands)
    assert {k: got[k] for k in case["expect"]} == case["expect"]


def test_leader_cannot_pass_and_wrong_seat():
    g = Game(hands=[[("산", 1)], [("산", 2)], [("산", 3)], [("산", 4)]], today="벚", turn=0)
    with pytest.raises(IllegalMove):
        g.play(0, None)
    with pytest.raises(IllegalMove):
        g.play(1, [("산", 2)])
```

- [ ] **Step 2: 실패 확인** — `ModuleNotFoundError: kumoniji.game`
- [ ] **Step 3: 구현** — `rules.simulate`의 반복문 한 바퀴를 메서드 하나로 옮긴 것이다.

```python
# kumoniji/server/kumoniji/game.py
"""한 판 진행 상태(서버 권위). rules.simulate와 같은 규칙을 한 수씩 적용한다."""
import random
from dataclasses import dataclass, field

from .rules import DECK, SHAPES, beats, first_player, settle, small_today, special_steps, value

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

    @classmethod
    def deal(cls, rng: random.Random) -> "Game":
        deck = DECK[:]
        rng.shuffle(deck)
        hands = [sorted(deck[i * 13:(i + 1) * 13], key=value) for i in range(4)]
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
        else:
            if any(t not in self.hands[seat] for t in move) or not beats(self.table, move):
                raise IllegalMove("낼 수 없는 패")
            for t in move:
                self.hands[seat].remove(t)
            self.pot += special_steps(move, self.today, finish=not self.hands[seat])
            self.doubles += len(move) == 5 and all(s == self.today for s, _ in move)
            self.table, self.last, self.passes = list(move), seat, 0
            if not self.hands[seat]:
                self.bonus[seat] += self.pot + small_today(move, self.today)
                self.pot, self.winner = 0, seat
                return
        self.turn = (self.turn + 1) % n

    def settlement(self) -> list[int] | None:
        return None if self.winner is None else settle(self.hands, self.petals, self.bonus, self.doubles)
```

- [ ] **Step 4: 통과 확인** — `pytest -q tests/test_game.py` 전부 PASS
- [ ] **Step 5: 커밋** — `feat: 쿠모니지 한 수씩 진행하는 게임 상태`

---

### Task 3: 봇 + 무작위 500판 대조

**Files:**
- Create: `kumoniji/server/kumoniji/bots.py`
- Modify: `kumoniji/server/tests/test_game.py`(테스트 추가)

**Interfaces:**
- Consumes: rules, Game
- Produces: `bots.plays(hand) -> list[list[Tile]]`, `bots.pick(kind: str, hand, table, today, rng) -> list[Tile] | None`(kind는 `"smart"` 또는 `"aim"`)

- [ ] **Step 1: 테스트 추가** — 봇끼리 친 판의 기록을 `rules.simulate`에 넣어 같은 결과가 나오고, 정산 합이 0인지 본다.

```python
import random

from kumoniji.bots import pick


def test_bot_games_match_simulate_and_zero_sum():
    rng = random.Random(20261118)
    for _ in range(500):
        g = Game.deal(rng)
        start = [list(h) for h in g.hands]
        moves = []
        while g.winner is None:
            m = pick("aim", g.hands[g.turn], g.table, g.today, rng)
            moves.append("패스" if m is None else m)
            g.play(g.turn, m)
        r = rules.simulate(start, moves, g.today)
        assert (r["error_at"], r["winner"], r["petals"], r["bonus"], r["doubles"]) == (None, g.winner, g.petals, g.bonus, g.doubles)
        assert sum(g.settlement()) == 0
```

- [ ] **Step 2: 실패 확인** — `ModuleNotFoundError: kumoniji.bots`
- [ ] **Step 3: 구현** — `제안_v4/sim.py`의 `plays`·`strength`·`choose`(18~60행)와 `sim_v4.py`의 `pick`(9~15행)을 그대로 옮긴다. import만 `from .rules import BOMBS, KINDS5, ODD_EVEN, SHAPES, STRAIGHTS, beats, classify, special_steps, value`와 `from itertools import combinations, product`로 바꾼다. 정산·통계 함수(`play_game` 이하)는 옮기지 않는다.
- [ ] **Step 4: 통과 확인** — `pytest -q` 전체 PASS
- [ ] **Step 5: 커밋** — `feat: 쿠모니지 봇`

---

### Task 4: API

**Files:**
- Create: `kumoniji/server/kumoniji/api.py`
- Test: `kumoniji/server/tests/test_api.py`

**Interfaces:**
- Consumes: Game, IllegalMove, bots.pick, bots.plays, rules.value
- Produces(HTTP, 앱이 씀):
  - `POST /api/games` → `GameView`
  - `GET /api/games/{id}` → `GameView`
  - `POST /api/games/{id}/moves` 본문 `{"tiles": ["s3", "m3"]}`(빈 목록 = 패스) → `GameView`. 사람이 낸 수 다음 봇들이 사람 차례나 판 끝까지 진행한다.
  - `GameView = {id, today, turn, hand: [str], counts: [int×4], table: [str], last: int|null, petals: [int×4], bonus: [int×4], doubles: int, winner: int|null, settlement: [int×4]|null, events: [{seat: int, tiles: [str]|null}]}` — 사람은 항상 0번 자리. 남의 손패는 장수만 준다.
  - 오류: 없는 판 404, 차례 아님·끝난 판 409, 규칙 위반·잘못된 표기 422

- [ ] **Step 1: 테스트 작성**

```python
# kumoniji/server/tests/test_api.py
import random

from fastapi.testclient import TestClient

from kumoniji.api import SUIT, app, dec
from kumoniji.bots import pick

c = TestClient(app)


def test_play_one_full_game():
    v = c.post("/api/games").json()
    assert len(v["hand"]) == v["counts"][0] and sum(v["counts"]) == 52 - sum(len(e["tiles"] or []) for e in v["events"])
    rng = random.Random(1)
    while v["winner"] is None:
        assert v["turn"] == 0
        hand, table = [dec(t) for t in v["hand"]], [dec(t) for t in v["table"]]
        m = pick("smart", hand, table, SUIT_TODAY(v), rng)
        v = c.post(f"/api/games/{v['id']}/moves", json={"tiles": [f"{SUIT[s]}{n}" for s, n in m] if m else []}).json()
    assert sum(v["settlement"]) == 0


def SUIT_TODAY(v):
    return {code: s for s, code in SUIT.items()}[v["today"]]


def test_errors():
    assert c.get("/api/games/nope").status_code == 404
    v = c.post("/api/games").json()
    assert c.post(f"/api/games/{v['id']}/moves", json={"tiles": ["x9"]}).status_code == 422
    if v["winner"] is None and not v["table"]:
        assert c.post(f"/api/games/{v['id']}/moves", json={"tiles": []}).status_code == 422  # 선은 패스 불가
```

- [ ] **Step 2: 실패 확인** — `uv run --no-project --with pytest --with httpx --with fastapi==0.136.3 pytest -q tests/test_api.py` → `ModuleNotFoundError`
- [ ] **Step 3: 구현**

```python
# kumoniji/server/kumoniji/api.py
"""쿠모니지 1단계 API: 사람(0번) 1명 + 봇 3명. 판은 메모리에만 둔다."""
import random
import secrets
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
GAMES: OrderedDict[str, tuple[Game, random.Random]] = OrderedDict()  # ponytail: 메모리 보관·재시작 시 사라짐, 계정 단계에서 DB로
app = FastAPI(title="kumoniji", docs_url=None, redoc_url=None)


def enc(t):
    return f"{SUIT[t[0]]}{t[1]}"


def dec(s: str):
    if len(s) < 2 or s[0] not in CODE or not s[1:].isdigit() or not 1 <= int(s[1:]) <= 13:
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
    return dict(id=gid, today=SUIT[g.today], turn=g.turn, hand=[enc(t) for t in sorted(g.hands[HUMAN], key=value)],
                counts=[len(h) for h in g.hands], table=[enc(t) for t in g.table], last=g.last,
                petals=[len(p) for p in g.petals], bonus=g.bonus, doubles=g.doubles, winner=g.winner,
                settlement=g.settlement(), events=events)


def load(gid: str) -> tuple[Game, random.Random]:
    if gid not in GAMES:
        raise HTTPException(404, "없는 판")
    return GAMES[gid]


@app.post("/api/games")
def new_game():
    rng = random.Random(secrets.randbits(64))
    g, gid, events = Game.deal(rng), secrets.token_urlsafe(12), []
    run_bots(g, rng, events)
    GAMES[gid] = (g, rng)
    while len(GAMES) > MAX_GAMES:
        GAMES.popitem(last=False)
    return view(gid, g, events)


@app.get("/api/games/{gid}")
def get_game(gid: str):
    return view(gid, load(gid)[0], [])


@app.post("/api/games/{gid}/moves")
def move(gid: str, body: Move):
    g, rng = load(gid)
    if g.winner is not None or g.turn != HUMAN:
        raise HTTPException(409, "차례가 아님")
    tiles = [dec(t) for t in body.tiles]
    try:
        g.play(HUMAN, tiles or None)
    except IllegalMove as e:
        raise HTTPException(422, str(e))
    events = [{"seat": HUMAN, "tiles": body.tiles or None}]
    run_bots(g, rng, events)
    return view(gid, g, events)


WEB = Path(__file__).resolve().parent.parent / "web"
if WEB.is_dir():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
```

- [ ] **Step 4: 통과 확인** — 서버 테스트 전체 PASS. 로컬 수동 확인: `uv run --no-project --with fastapi==0.136.3 --with uvicorn==0.49.0 uvicorn kumoniji.api:app --port 8300` 후 `curl -X POST localhost:8300/api/games`
- [ ] **Step 5: 커밋** — `feat: 쿠모니지 1단계 API`

---

### Task 5: 패 그림 낱장 내보내기 (Codex)

**Files:**
- Create: `kumoniji/app/assets/tiles/{m,s,l,c}{1..13}.svg`(52장), `back.svg`

- [ ] **Step 1: Codex에게 지시** — 원본은 바탕화면 `시안_v3/codex_F16.svg`. 패 한 장 = 독립 SVG(viewBox 0 0 120 160), 안쪽 그림·숫자·무늬 아이콘은 F16 그대로. 1~10은 기본 캐릭터, 11~13은 05 영역 날씨 장면 + 모서리 단독 문양 + 동·은·금 이중 테두리. 벚꽃은 ②우산콩. 외부 폰트 쓰지 말 것(숫자는 path로) — 앱에서 폰트가 없어도 같게 보이게.
- [ ] **Step 2: 검증** — 52+1장을 한 장에 모은 대조표 SVG를 만들어 헤드리스 크롬으로 PNG 렌더 → 직접 보고 빠진 장·뒤바뀐 무늬·숫자 확인. `ls assets/tiles | wc -l` == 53.
- [ ] **Step 3: 커밋** — `feat: 쿠모니지 패 그림 53장`

---

### Task 6: Flutter 앱 (웹)

**Files:**
- Create: `kumoniji/app/` (`flutter create --platforms=web,android,ios --project-name kumoniji app`으로 시작 후 아래만 남김)
- `pubspec.yaml`: `http: ^1.6.0`, `flutter_svg`(pub get 때 최신 안정판 고정), `flutter_localizations`, `intl`, `generate: true`, assets `assets/tiles/`
- `lib/api.dart`, `lib/tile.dart`, `lib/table_screen.dart`, `lib/main.dart`, `lib/l10n/app_{en,ja,ko}.arb`, `l10n.yaml`
- Test: `test/api_test.dart`, `test/tile_test.dart`

**Interfaces:**
- Consumes: Task 4의 `GameView` JSON, Task 5의 `assets/tiles/<코드>.svg`
- Produces: `class GameState.fromJson(Map)`, `class Api { Future<GameState> newGame(); Future<GameState> move(String id, List<String> tiles); }`, `TileView(code, selected, onTap)`

- [ ] **Step 1: 테스트 작성**

```dart
// test/api_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:kumoniji/api.dart';

void main() {
  test('GameState parses server view', () {
    final s = GameState.fromJson({
      'id': 'a', 'today': 's', 'turn': 0, 'hand': ['m1', 's3'], 'counts': [2, 13, 13, 13],
      'table': [], 'last': null, 'petals': [0, 0, 0, 0], 'bonus': [0, 0, 0, 0], 'doubles': 0,
      'winner': null, 'settlement': null,
      'events': [{'seat': 1, 'tiles': null}],
    });
    expect(s.hand, ['m1', 's3']);
    expect(s.events.single.tiles, isNull);
    expect(s.finished, isFalse);
  });
}
```

```dart
// test/tile_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kumoniji/tile.dart';

void main() {
  testWidgets('tap toggles selection callback', (t) async {
    var taps = 0;
    await t.pumpWidget(MaterialApp(home: TileView(code: 's3', selected: false, onTap: () => taps++)));
    await t.tap(find.byType(TileView));
    expect(taps, 1);
  });
}
```

- [ ] **Step 2: 실패 확인** — `source ~/.cache/gildle-build/env.sh && cd kumoniji/app && flutter test` → 컴파일 오류
- [ ] **Step 3: 구현**

```dart
// lib/api.dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class Play {
  final int seat;
  final List<String>? tiles;
  Play(this.seat, this.tiles);
}

class GameState {
  final String id, today;
  final int turn, doubles;
  final int? last, winner;
  final List<String> hand, table;
  final List<int> counts, petals, bonus;
  final List<int>? settlement;
  final List<Play> events;
  GameState.fromJson(Map<String, dynamic> j)
      : id = j['id'], today = j['today'], turn = j['turn'], doubles = j['doubles'],
        last = j['last'], winner = j['winner'],
        hand = List<String>.from(j['hand']), table = List<String>.from(j['table']),
        counts = List<int>.from(j['counts']), petals = List<int>.from(j['petals']),
        bonus = List<int>.from(j['bonus']),
        settlement = j['settlement'] == null ? null : List<int>.from(j['settlement']),
        events = [for (final e in j['events']) Play(e['seat'], e['tiles'] == null ? null : List<String>.from(e['tiles']))];
  bool get finished => winner != null;
}

class ApiError implements Exception {
  final int status;
  ApiError(this.status);
}

class Api {
  // 웹은 같은 주소(서버가 앱을 냄), 개발 때는 --dart-define=API=http://localhost:8300
  final String base = const String.fromEnvironment('API', defaultValue: '');
  Future<GameState> newGame() => _post('/api/games', null);
  Future<GameState> move(String id, List<String> tiles) => _post('/api/games/$id/moves', {'tiles': tiles});
  Future<GameState> _post(String path, Object? body) async {
    final r = await http.post(Uri.parse('$base$path'),
        headers: {'content-type': 'application/json'}, body: body == null ? null : jsonEncode(body));
    if (r.statusCode != 200) throw ApiError(r.statusCode);
    return GameState.fromJson(jsonDecode(utf8.decode(r.bodyBytes)));
  }
}
```

```dart
// lib/tile.dart
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

class TileView extends StatelessWidget {
  final String code;
  final bool selected;
  final VoidCallback? onTap;
  final double width;
  const TileView({super.key, required this.code, this.selected = false, this.onTap, this.width = 56});
  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: AnimatedSlide(
          offset: selected ? const Offset(0, -0.18) : Offset.zero,
          duration: const Duration(milliseconds: 120),
          child: SvgPicture.asset('assets/tiles/$code.svg', width: width),
        ),
      );
}
```

`lib/table_screen.dart` — 한 화면에 다음을 둔다(StatefulWidget, `GameState? s`, `Set<String> picked`):
- 위·왼쪽·오른쪽: 봇 3명(뒷면 `back.svg` + 남은 장수, 꽃잎 수, 보너스).
- 가운데: 바닥 패(`s.table`), 오늘의 무늬 배지(`assets/tiles/<today>1.svg` 작은 아이콘 + "Today"), ×5가 걸렸으면 `×5^doubles` 표시.
- 아래: 내 손패를 겹쳐 가로로(`TileView`, 탭하면 `picked` 토글), 버튼 Play(`picked` 비면 비활성)·Pass(바닥이 비면 비활성).
- 서버 응답의 `events`는 0.6초 간격으로 하나씩 보여 준 뒤(`Future.delayed`) 최종 상태로 바꾼다 — 봇이 "생각하는" 흐름.
- 422면 SnackBar "That play isn't allowed"(언어별), 판이 끝나면 다이얼로그에 네 사람 점수(`settlement`)와 New game 버튼.

```dart
// lib/table_screen.dart (핵심 흐름)
Future<void> _apply(Future<GameState> call) async {
  try {
    final next = await call;
    for (final e in next.events) {
      if (!mounted) return;
      setState(() => _flash = e);            // 누가 무엇을 냈는지 가운데에 잠깐
      await Future.delayed(const Duration(milliseconds: 600));
    }
    setState(() { s = next; picked.clear(); _flash = null; });
    if (next.finished) _showResult(next);
  } on ApiError catch (e) {
    if (e.status == 422 && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.illegal)));
    }
  }
}
```

ARB 키(세 언어 모두): `title`, `newGame`, `play`, `pass`, `today`, `illegal`, `youWin`, `points`(예: en "{n} pts", ja "{n}点", ko "{n}점").

- [ ] **Step 4: 검증** — `flutter analyze`(경고 0) · `flutter test` PASS · `flutter build web --dart-define=API=http://localhost:8300` 후 서버(Task 4)를 띄우고 `build/web`을 정적 서버로 열어 헤드리스 크롬으로 시작 화면·내 차례·결과 다이얼로그를 캡처해 직접 본다(메모리 규칙: UI는 캡처 확인 후 배포).
- [ ] **Step 5: 커밋** — `feat: 쿠모니지 웹 앱 1단계`

---

### Task 7: 컨테이너 · k3s · CI

**Files:**
- Create: `kumoniji/Dockerfile`, `kumoniji/deploy.sh`, `k8s/kumoniji.yaml`, `.github/workflows/kumoniji-ci.yml`

- [ ] **Step 1: Dockerfile** — 두 단계. Flutter 이미지에서 `flutter build web --release` → `python:3.13-slim`에 `server/`와 `build/web`을 `/srv/web`으로 복사.

```dockerfile
FROM ghcr.io/cirruslabs/flutter:3.47.2 AS web
WORKDIR /app
COPY app/ .
RUN flutter pub get && flutter build web --release

FROM python:3.13-slim
WORKDIR /srv
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server/kumoniji ./kumoniji
COPY --from=web /app/build/web ./web
USER 10001
CMD ["uvicorn", "kumoniji.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

`api.py`의 `WEB`은 `kumoniji/` 한 단계 위 `web/`이므로 `/srv/web`과 맞는다.

- [ ] **Step 2: k8s/kumoniji.yaml** — Deployment(replicas 1, image `kumoniji:latest`, `imagePullPolicy: Never`, requests 50m/64Mi·limits 500m/256Mi, readinessProbe `GET /` 200), Service `kumoniji:8000`, Ingress host `kumoniji.suvisdev.cloud` → kumoniji:8000(traefik). 판이 메모리에 있으므로 replicas는 1로 고정(주석으로 이유).
- [ ] **Step 3: deploy.sh** — `docker build -t kumoniji:latest kumoniji && docker save kumoniji:latest | sudo k3s ctr images import - && kubectl apply -f k8s/kumoniji.yaml && kubectl -n suvisdev rollout restart deploy/kumoniji && kubectl -n suvisdev rollout status deploy/kumoniji`(기존 deploy.sh와 같은 import 방식).
- [ ] **Step 4: CI** — gildle-ci.yml과 같은 형식. paths `kumoniji/**`. job 둘: server(`pip install -r requirements.txt pytest httpx && pytest -q`), app(flutter 3.47.2 `pub get`·`analyze`·`test`).
- [ ] **Step 5: 검증** — 로컬 `docker build` 성공 → `docker run -p 8300:8000 kumoniji:latest` → `curl -s localhost:8300/ | grep -c flutter` ≥ 1, `curl -X POST localhost:8300/api/games` 200. 그다음 deploy.sh로 k3s 배포 → `kubectl -n suvisdev get pods`에 kumoniji Running, `curl -H 'Host: kumoniji.suvisdev.cloud' localhost/` 200.
- [ ] **Step 6: 사용자 작업 안내** — Cloudflare Zero Trust → 터널 → Public Hostname 추가: `kumoniji.suvisdev.cloud` → 기존 `api.suvisdev.cloud`와 같은 대상(Traefik). 추가 후 `curl -I https://kumoniji.suvisdev.cloud` 200 확인.
- [ ] **Step 7: 커밋** — `feat: 쿠모니지 배포 구성과 CI`

---

### Task 8: 문서

- [ ] RULES.md를 v4로 다시 쓴다(바탕화면 `기획문서_하네스/`, 이전 본은 `이전버전/`으로), README 결정 기록에 "규칙 v4 확정(11-18)·×5 조건 보류·쿠모니지·날씨 문양·금은동 테두리·1단계 범위" 추가, PDF 재생성.
- [ ] ADR `_docs/decisions/0014-쿠모니지-서버-권위와-단일-컨테이너.md`: 서버 권위(멀티 단계에서 엔진 재사용·치팅 방지) / 버린 대안: 앱 안에서 판정(Dart로 규칙을 한 번 더 짜야 하고 멀티 때 서버로 다시 옮김), 웹 정적 파일 따로 호스팅(컨테이너·라우팅이 둘).
- [ ] `_docs/WORK_LOG_MAINPAGE.md`, `_docs/INTERVIEW_QUESTIONS.md`, `_docs/LESSONS.md`(있으면), 메모리 `tile-game-project.md` 갱신.
- [ ] 커밋 → codex_gate 리뷰 → PR → CI → 머지(자동 마무리 규칙). main 머지가 backend-deploy를 부르지 않는지(paths가 suvisdev/만인지) 확인.

---

## 1단계에서 하지 않는 것 (다음 단계)
- 2단계: 4인 멀티(WebSocket·매칭·같은 IP 금지) — 이때 계정 필요
- 3단계: 계정(구글+자체)·재화·하트·DB — SECURITY.md 하네스 48개를 테스트로 옮김
- 4단계: 결제·약관 빈칸 292곳·사업자 정보
- 봇 난이도 여러 단계, 효과음·애니메이션 다듬기
