import random

from fastapi.testclient import TestClient

from kumoniji.api import CODE, SUIT, app, dec
from kumoniji.bots import pick

c = TestClient(app)


def test_play_one_full_game():
    v = c.post("/api/games").json()
    played = sum(len(e["tiles"] or []) for e in v["events"])
    assert len(v["hand"]) == v["counts"][0] and sum(v["counts"]) == 52 - played
    rng = random.Random(1)
    while v["winner"] is None:
        assert v["turn"] == 0
        hand, table = [dec(t) for t in v["hand"]], [dec(t) for t in v["table"]]
        m = pick("smart", hand, table, CODE[v["today"]], rng)
        body = {"tiles": [f"{SUIT[s]}{n}" for s, n in m] if m else []}
        v = c.post(f"/api/games/{v['id']}/moves", json=body).json()
    assert sum(v["settlement"]) == 0
    assert c.post(f"/api/games/{v['id']}/moves", json={"tiles": []}).status_code == 409


def test_errors():
    assert c.get("/api/games/nope").status_code == 404
    v = c.post("/api/games").json()
    assert (
        c.post(f"/api/games/{v['id']}/moves", json={"tiles": ["x9"]}).status_code == 422
    )
    assert (
        c.post(f"/api/games/{v['id']}/moves", json={"tiles": ["s1"] * 6}).status_code
        == 422
    )
    if not v["table"]:
        assert (
            c.post(f"/api/games/{v['id']}/moves", json={"tiles": []}).status_code == 422
        )  # 선은 패스 불가
    assert c.get(f"/api/games/{v['id']}").json()["hand"] == v["hand"]


def test_hidden_hands():
    v = c.post("/api/games").json()
    assert set(v) == {
        "id",
        "today",
        "turn",
        "hand",
        "counts",
        "table",
        "last",
        "petals",
        "bonus",
        "doubles",
        "winner",
        "settlement",
        "events",
        "playable",
        "moves",
        "plays",
        "passed",
        "suits",
    }


def test_concurrent_same_move_applies_once(monkeypatch):
    """같은 수를 8번 동시에 보내도 한 번만 적용된다(나머지는 차례 아님 409 또는 낼 수 없음 422).
    판정(차례 확인 → 손패 제거) 사이에 지연을 넣어 겹칠 틈을 벌린다 — 잠금이 없으면 손패를 두 번 지우려다 500이 난다."""
    import time
    from concurrent.futures import ThreadPoolExecutor

    from kumoniji import game

    real_beats = game.beats

    def slow_beats(prev, new):
        time.sleep(0.02)
        return real_beats(prev, new)

    monkeypatch.setattr(game, "beats", slow_beats)

    def send(url, body):
        return c.post(url, json=body).status_code

    for _ in range(5):
        v = c.post("/api/games").json()
        hand, table = [dec(t) for t in v["hand"]], [dec(t) for t in v["table"]]
        m = pick("smart", hand, table, CODE[v["today"]], random.Random(0))
        if (
            m is None
        ):  # 패스는 봇이 한 바퀴 돈 뒤 다시 낼 수 있어 '한 번만'을 확인할 수 없다
            continue
        body = {"tiles": [f"{SUIT[s]}{n}" for s, n in m]}
        url = f"/api/games/{v['id']}/moves"
        with ThreadPoolExecutor(8) as ex:
            codes = list(ex.map(send, [url] * 8, [body] * 8))
        assert codes.count(200) == 1 and set(codes) <= {200, 409, 422}
        assert c.get(f"/api/games/{v['id']}").json()["counts"][0] == len(
            v["hand"]
        ) - len(body["tiles"])


def test_full_store_evicts_least_recently_used(monkeypatch):
    from kumoniji import api

    monkeypatch.setattr(api, "MAX_GAMES", 3)
    ids = [c.post("/api/games").json()["id"] for _ in range(3)]
    c.get(f"/api/games/{ids[0]}")  # 첫 판을 다시 씀 → 가장 오래 안 쓴 판은 ids[1]
    c.post("/api/games")
    assert c.get(f"/api/games/{ids[0]}").status_code == 200
    assert c.get(f"/api/games/{ids[1]}").status_code == 404


def test_create_rate_limit_per_ip(monkeypatch):
    from kumoniji import api

    monkeypatch.setattr(api, "CREATE_PER_MIN", 2)
    api.CREATES.clear()
    h = {"cf-connecting-ip": "203.0.113.9"}
    assert [c.post("/api/games", headers=h).status_code for _ in range(3)] == [
        200,
        200,
        429,
    ]
    assert (
        c.post("/api/games", headers={"cf-connecting-ip": "203.0.113.10"}).status_code
        == 200
    )


def test_suit_order_and_playable_and_reason():
    from kumoniji import api
    from kumoniji.game import Game

    g = Game(
        hands=[
            [("벚", 7), ("산", 2), ("솜", 3)],
            [("잎", 9)],
            [("솜", 9)],
            [("산", 9)],
        ],
        today="잎",
        turn=0,
        table=[("잎", 7)],
        last=3,
    )
    api.GAMES["fixed"] = (g, random.Random(0))
    v = c.get("/api/games/fixed").json()
    assert v["suits"] == ["m", "s", "l", "c"]  # 산 > 벚꽃 > 잎사귀 > 솜사탕 (11-18)
    assert v["playable"] == ["s7"]  # 벚7만 잎7을 이긴다
    assert v["moves"] == [["s7"]]
    r = c.post("/api/games/fixed/moves", json={"tiles": ["m2"]})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "weaker"
    g.table = [("산", 7)]
    r = c.post("/api/games/fixed/moves", json={"tiles": ["s7"]})
    assert r.json()["detail"]["code"] == "suit"  # 같은 숫자인데 무늬가 약함
    assert c.get("/api/games/fixed").json()["playable"] == []
    r = c.post("/api/games/fixed/moves", json={"tiles": ["s7", "m2"]})
    assert r.json()["detail"]["code"] == "not_combo"


def test_seat_plays_and_passed_follow_the_round():
    from kumoniji.game import Game

    g = Game(
        hands=[
            [("솜", 2), ("솜", 9)],
            [("솜", 3), ("솜", 10)],
            [("솜", 4), ("솜", 11)],
            [("솜", 5), ("솜", 12)],
        ],
        today="잎",
        turn=0,
    )
    for seat, t in enumerate([("솜", 2), ("솜", 3), ("솜", 4), ("솜", 5)]):
        g.play(seat, [t])
    from kumoniji import api

    assert api.view("x", g, [])["plays"] == [["c2"], ["c3"], ["c4"], ["c5"]]

    g.play(0, None)
    g.play(1, None)
    assert api.view("x", g, [])["passed"] == [0, 1]  # 3번이 낸 뒤 0·1번이 패스
    g.play(2, None)  # 셋 패스 → 3번이 바퀴를 가져감
    assert api.view("x", g, [])["passed"] == []
    assert api.view("x", g, [])["plays"] == [None] * 4
    assert g.history == [] and g.table == []


def test_human_auto_passes_when_nothing_beats_table():
    """사람이 바닥(산13 = 가장 센 싱글)을 이길 패가 없으면 서버가 사람 차례를 자동 패스로 넘긴다."""
    from kumoniji import api
    from kumoniji.game import Game

    g = Game(
        hands=[
            [("솜", 2), ("벚", 5)],
            [("잎", 3), ("솜", 8)],
            [("솜", 4), ("잎", 9)],
            [("솜", 6), ("산", 10)],
        ],
        today="잎",
        turn=3,
    )
    g.play(3, [("솜", 6)])
    g.table, g.passes = [("산", 13)], 2  # 3번이 산13, 1·2번은 이미 패스 → 다음은 사람(0번)
    g.turn = 0
    events = []
    api.run_bots(g, random.Random(0), events)
    assert events[0] == {"seat": 0, "tiles": None}  # 사람 자동 패스로 바퀴가 끝남
    assert g.petals[3] == ["산"]  # 3번이 바퀴를 가져감


def test_no_auto_pass_when_someone_else_could_still_beat():
    """사람은 못 이겨도 남의 손에 이길 패(산13)가 남아 있으면 자동 패스하지 않는다 — 자동 패스가 사람 손패를 드러내지 않게."""
    from kumoniji import api
    from kumoniji.game import Game

    g = Game(
        hands=[
            [("솜", 2), ("벚", 5)],
            [("산", 13), ("솜", 8)],
            [("솜", 4), ("잎", 9)],
            [("솜", 6), ("산", 10)],
        ],
        today="잎",
        turn=0,
        table=[("벚", 13)],
        last=3,
    )
    events = []
    api.run_bots(g, random.Random(0), events)
    assert events == [] and g.turn == 0  # 사람이 직접 패스해야 함
    assert api.view("x", g, [])["moves"] == []
    g.hands[1].remove(("산", 13))  # 산13이 이미 나왔다면 아무도 못 이김 → 자동 패스
    api.run_bots(g, random.Random(0), events)
    assert events[0] == {"seat": 0, "tiles": None}


def test_can_beat_by_size():
    from kumoniji.api import can_beat

    assert not can_beat([("산", 13)], [("벚", 13), ("산", 12)])
    assert can_beat([("벚", 13)], [("산", 13)])
    assert can_beat([("솜", 9), ("잎", 9)], [("벚", 10), ("솜", 10)])
    assert not can_beat([("솜", 9), ("잎", 9)], [("벚", 10), ("솜", 11)])
    straight = [("솜", 1), ("잎", 2), ("벚", 3), ("산", 4), ("솜", 5)]
    assert can_beat(straight, [("솜", 2), ("잎", 3), ("벚", 4), ("산", 5), ("솜", 6)])
    assert not can_beat(straight, [("솜", 2), ("잎", 3), ("벚", 4), ("산", 5)])


def test_web_files_are_revalidated():
    """웹 파일은 배포마다 이름이 같아 캐시되면 옛 앱이 남는다 → no-cache. API는 건드리지 않는다."""
    assert c.get("/main.dart.js").headers["cache-control"] == "no-cache"
    assert "cache-control" not in c.get("/api/games/nope").headers
