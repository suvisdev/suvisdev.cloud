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
