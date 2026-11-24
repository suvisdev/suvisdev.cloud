"""/api/ws — 실제 Postgres 세션으로 인증(계획 C Task 5). 한 TestClient(한 이벤트 루프) 안에서 소켓 여러 개를 연다."""

import asyncio
from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from kumoniji.accounts import db, sessions
from kumoniji.api import app
from kumoniji.multi import ws as multi_ws
from kumoniji.multi.lobby import Lobby

from .helpers import ORIGIN, browser, login, make_account, signed_up

APP = {"x-kumoniji-client": "app"}


@pytest.fixture
def server(outbox, fast_hash, monkeypatch):
    monkeypatch.setattr(multi_ws, "LOBBY", Lobby())
    multi_ws.CONNS.clear()
    multi_ws.LAST_Q.clear()
    with TestClient(app, base_url=ORIGIN) as c, ExitStack() as opened:
        c.opened = opened  # connect()로 연 소켓 — 닫지 않으면 서버 쪽 처리가 남아 TestClient 종료가 멈춘다
        yield c
    multi_ws.CONNS.clear()


def account(outbox, n: int) -> str:
    """가입·인증·앱 로그인 → 액세스 토큰."""
    email = f"p{n}@x.com"
    signed_up(browser(), outbox, email=email, nick=f"p{n}")
    return login(TestClient(app, base_url=ORIGIN, headers=APP), email=email).json()["access"]


def connect(server, token: str, n: int = 0, first: str = "lobby"):
    """앱처럼 Origin 없이 붙어 첫 메시지로 인증. 기기·IP를 달리해 자동 매칭의 같은 사람 거르기를 피한다."""
    w = server.opened.enter_context(
        server.websocket_connect("/api/ws", headers={"x-kumoniji-device": f"dev{n}", "cf-connecting-ip": f"10.0.0.{n}"})
    )
    w.send_json({"t": "auth", "token": token})
    assert w.receive_json()["t"] == first
    return w


def until(w, kind: str) -> dict:
    while (m := w.receive_json())["t"] != kind:
        pass
    return m


def closed_with(w) -> int:
    with pytest.raises(WebSocketDisconnect) as e:
        while True:
            w.receive_json()
    return e.value.code


def test_other_origin_is_rejected(server):
    with pytest.raises(WebSocketDisconnect) as e, server.websocket_connect(
        "/api/ws", headers={"origin": "https://evil.example"}
    ):
        pass
    assert e.value.code == 4403


def test_browser_cookie_with_own_origin(server, outbox):
    c = browser()
    signed_up(c, outbox)
    login(c)
    cookie = "; ".join(f"{k}={v}" for k, v in c.cookies.items())
    with server.websocket_connect("/api/ws", headers={"origin": ORIGIN, "cookie": cookie}) as w:
        assert w.receive_json() == {"t": "lobby"}


@pytest.mark.parametrize("first", [{"t": "auth", "token": "garbage"}, {"t": "queue"}, {"t": "auth", "token": 5}])
def test_bad_or_missing_token_is_rejected(server, first):
    with server.websocket_connect("/api/ws") as w:
        w.send_json(first)
        assert closed_with(w) == 4401


def test_unverified_account_is_rejected(server):
    a = make_account("u@x.com", "u", verified=False)
    with db.tx() as c:
        token, _ = sessions.create(c, a, mfa_passed=False)
    with server.websocket_connect("/api/ws") as w:
        w.send_json({"t": "auth", "token": token})
        assert closed_with(w) == 4401


def test_big_message_and_flood_close(server, outbox):
    t = account(outbox, 1)
    w = connect(server, t)
    w.send_text("x" * 3000)
    assert closed_with(w) == 1009
    w = connect(server, t)
    for _ in range(12):
        w.send_json({"t": "ping"})
    assert closed_with(w) == 1008


def test_new_connection_replaces_old_and_keeps_queue(server, outbox):
    t = account(outbox, 1)
    old = connect(server, t)
    old.send_json({"t": "queue"})
    assert until(old, "queued")["waiting"] == 1
    connect(server, t, first="queued")  # 같은 계정 새 연결 — 아직 대기 중이라고 알려 준다
    assert closed_with(old) == 4409
    other = connect(server, account(outbox, 2), 2)
    other.send_json({"t": "queue"})
    assert until(other, "queued")["waiting"] == 2  # 옛 연결이 닫혀도 대기열에 그대로


def test_logout_closes_socket_on_recheck(server, outbox, monkeypatch):
    monkeypatch.setattr(multi_ws, "RECHECK", 0.3)
    t = account(outbox, 1)
    w = connect(server, t)
    TestClient(app, base_url=ORIGIN, headers={**APP, "authorization": f"Bearer {t}"}).post("/api/auth/logout")
    assert closed_with(w) == 4401


def test_idle_socket_closes(server, outbox, monkeypatch):
    monkeypatch.setattr(multi_ws, "IDLE", 0.3)
    w = connect(server, account(outbox, 1))
    assert closed_with(w) == 4408


def test_four_sockets_match_and_play_a_full_game(server, outbox, monkeypatch):
    monkeypatch.setattr(multi_ws, "clock", lambda: 1000.0)  # 시간이 멈춰 있어 타이머가 끼어들지 않는다
    monkeypatch.setattr(multi_ws, "RATE", 10_000)  # 테스트는 사람보다 훨씬 빨리 보낸다(초당 제한은 따로 시험)
    ws = [connect(server, account(outbox, n), n) for n in range(4)]
    for w in ws:
        w.send_json({"t": "queue"})
    states = [until(w, "state") for w in ws]
    assert sorted(s["seat"] for s in states) == [0, 1, 2, 3]
    assert len({s["id"] for s in states}) == 1
    for s in states:
        assert len(s["hand"]) == s["counts"][s["seat"]]
    while states[0]["winner"] is None:
        me = next(i for i, s in enumerate(states) if s["seat"] == s["turn"])
        other = ws[(me + 1) % 4]
        other.send_json({"t": "move", "game": states[0]["id"], "ply": states[0]["ply"], "tiles": []})
        assert until(other, "error")["code"] == "not_your_turn"
        moves = states[me]["moves"]
        ws[me].send_json({"t": "move", "game": states[me]["id"], "ply": states[me]["ply"], "tiles": moves[0] if moves else []})
        states = [until(w, "state") for w in ws]
    assert sum(states[0]["settlement"]) == 0
    assert all(s["deadline"] is None for s in states)


def test_timer_auto_passes_and_pushes_to_everyone(server, outbox, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(multi_ws, "clock", lambda: now[0])
    ws = [connect(server, account(outbox, n), n) for n in range(4)]
    for w in ws:
        w.send_json({"t": "queue"})
    start = [until(w, "state") for w in ws]
    turn = start[0]["turn"]
    now[0] = start[0]["deadline"]  # 20초 지남 → 타이머(0.5초 간격)가 그 차례를 패스
    after = [until(w, "state") for w in ws]
    for s in after:
        assert s["events"][0] == {"seat": turn, "tiles": None}
        assert s["deadline"] == now[0] + 20


def test_browsers_without_device_header_still_match(server, outbox, monkeypatch):
    """브라우저는 기기 머리글을 못 단다 — 같은 User-Agent여도 IP가 다르면 한 판."""
    monkeypatch.setattr(multi_ws, "clock", lambda: 1000.0)
    ws = []
    for n in range(4):
        w = server.opened.enter_context(
            server.websocket_connect("/api/ws", headers={"user-agent": "Same/1.0", "cf-connecting-ip": f"10.0.1.{n}"})
        )
        w.send_json({"t": "auth", "token": account(outbox, n)})
        until(w, "lobby")
        w.send_json({"t": "queue"})
        ws.append(w)
    assert len({until(w, "state")["id"] for w in ws}) == 1


def test_oversized_first_auth_message_is_rejected(server, outbox):
    t = account(outbox, 1)
    with server.websocket_connect("/api/ws") as w:
        w.send_text('{"t":"auth","token":"%s"}' % t + " " * 3000)
        assert closed_with(w) == 4401


def test_reconnect_after_game_end_shows_result_and_unqueue_reports_game(server, outbox, monkeypatch):
    monkeypatch.setattr(multi_ws, "clock", lambda: 1000.0)
    monkeypatch.setattr(multi_ws, "RATE", 10_000)
    tokens = [account(outbox, n) for n in range(4)]
    ws = [connect(server, tokens[n], n) for n in range(4)]
    for w in ws:
        w.send_json({"t": "queue"})
    states = [until(w, "state") for w in ws]
    ws[3].send_json({"t": "unqueue"})  # 이미 매칭된 뒤의 취소 → lobby가 아니라 판 상태
    assert until(ws[3], "state")["id"] == states[0]["id"]
    while states[0]["winner"] is None:
        me = next(i for i, s in enumerate(states) if s["seat"] == s["turn"])
        moves = states[me]["moves"]
        ws[me].send_json({"t": "move", "game": states[me]["id"], "ply": states[me]["ply"], "tiles": moves[0] if moves else []})
        states = [until(w, "state") for w in ws]
    # 결과를 못 보고 끊겼다가 다시 붙은 사람 → 로비가 아니라 끝난 판 결과
    again = server.opened.enter_context(server.websocket_connect("/api/ws", headers={"x-kumoniji-device": "dev1"}))
    again.send_json({"t": "auth", "token": tokens[1]})
    result = again.receive_json()
    assert result["t"] == "state" and result["id"] == states[0]["id"]
    assert result["winner"] == states[0]["winner"] and result["settlement"] == states[1]["settlement"]
    again.send_json({"t": "queue"})  # 다시 대기했다가 취소 → 옛 결과가 아니라 로비
    until(again, "queued")
    again.send_json({"t": "unqueue"})
    assert again.receive_json() == {"t": "lobby"}


def test_access_token_expiry_closes_unless_renewed(server, outbox, monkeypatch):
    """소켓도 액세스 토큰 만료를 지킨다(탈취한 토큰으로 계속 못 쓰게). 앱은 갱신한 토큰을 보내 대기열을 잃지 않고 이어 간다."""
    import time

    monkeypatch.setattr(sessions, "ACCESS_TTL", 3)  # 만료 시각은 초 단위 정수라 간격을 넉넉히
    signed_up(browser(), outbox, email="r@x.com", nick="renewer")
    app_client = TestClient(app, base_url=ORIGIN, headers=APP)
    tokens = login(app_client, email="r@x.com").json()
    renewing = connect(server, tokens["access"], 1)
    renewing.send_json({"t": "queue"})
    until(renewing, "queued")
    time.sleep(2)
    fresh = app_client.post("/api/auth/refresh", json={"refresh": tokens["refresh"]}).json()["access"]
    renewing.send_json({"t": "auth", "token": fresh})
    time.sleep(2)  # 처음 토큰(3초)은 만료됐다
    renewing.send_json({"t": "ping"})
    assert until(renewing, "pong") == {"t": "pong"}
    assert [p.account for p in multi_ws.LOBBY.queue] != []  # 대기열 그대로

    lazy = connect(server, account(outbox, 2), 2)  # 갱신하지 않으면 만료 때 닫힌다
    assert closed_with(lazy) == 4401


def test_renewal_with_other_session_token_is_refused(server, outbox):
    w = connect(server, account(outbox, 1), 1)
    other = account(outbox, 2)
    w.send_json({"t": "auth", "token": other})
    assert until(w, "error") == {"t": "error", "code": "auth"}


def test_session_idle_for_30_days_closes_socket(server, outbox, monkeypatch):
    monkeypatch.setattr(multi_ws, "RECHECK", 0.3)
    w = connect(server, account(outbox, 1))
    with db.tx() as c:  # 리프레시 없이 30일 지난 세션 — HTTP로는 새 토큰을 못 받는다
        c.execute("UPDATE sessions SET last_used_at = now() - interval '31 days'")
    assert closed_with(w) == 4401


def test_unauthenticated_connections_per_ip_are_capped(server):
    head = {"cf-connecting-ip": "10.9.9.9"}
    for _ in range(multi_ws.PENDING_PER_IP):
        server.opened.enter_context(server.websocket_connect("/api/ws", headers=head))  # 인증 메시지 안 보냄
    with pytest.raises(WebSocketDisconnect), server.websocket_connect("/api/ws", headers=head):  # 업그레이드 전 거절
        pass
    with server.websocket_connect("/api/ws", headers={"cf-connecting-ip": "10.9.9.10"}) as w:  # 다른 IP는 된다
        w.send_json({"t": "auth", "token": "x"})
        assert closed_with(w) == 4401


def test_slow_recheck_closes_socket(server, outbox, monkeypatch):
    import time

    monkeypatch.setattr(multi_ws, "RECHECK", 0.2)
    monkeypatch.setattr(multi_ws, "AUTH_WAIT", 0.3)
    w = connect(server, account(outbox, 1))
    monkeypatch.setattr(multi_ws.web, "socket_alive", lambda s: time.sleep(1) or True)  # DB가 늦음
    assert closed_with(w) == 4401


def test_unqueue_by_outsider_does_not_spam_waiters(server, outbox):
    waiter = connect(server, account(outbox, 1), 1)
    waiter.send_json({"t": "queue"})
    assert until(waiter, "queued")["waiting"] == 1
    outsider = connect(server, account(outbox, 2), 2)
    for _ in range(3):
        outsider.send_json({"t": "unqueue"})
        assert until(outsider, "lobby") == {"t": "lobby"}
    waiter.send_json({"t": "ping"})
    assert waiter.receive_json() == {"t": "pong"}  # 그사이 'queued' 재전송이 끼지 않았다


def test_binary_frame_closes_with_unsupported_data(server, outbox):
    w = connect(server, account(outbox, 1))
    w.send_bytes(b'{"t":"ping"}')
    assert closed_with(w) == 1003


def test_messages_are_handled_while_recheck_is_slow(server, outbox, monkeypatch):
    """재확인이 DB를 기다리는 중에도 수는 바로 처리된다."""
    import time

    monkeypatch.setattr(multi_ws, "RECHECK", 0.1)
    w = connect(server, account(outbox, 1))
    monkeypatch.setattr(multi_ws.web, "socket_alive", lambda s: time.sleep(1.5) or True)
    time.sleep(0.2)  # 재확인이 도는 중
    start = time.perf_counter()
    w.send_json({"t": "ping"})
    assert until(w, "pong") == {"t": "pong"}
    assert time.perf_counter() - start < 0.5  # 재확인은 1.5초 걸린다 — 기다렸다면 넘는다


def test_revoked_session_leaves_queue_at_once(server, outbox, monkeypatch):
    monkeypatch.setattr(multi_ws, "RECHECK", 0.1)
    w = connect(server, account(outbox, 1))
    w.send_json({"t": "queue"})
    until(w, "queued")
    monkeypatch.setattr(multi_ws.web, "socket_alive", lambda s: False)  # 로그아웃 등
    assert closed_with(w) == 4401
    assert multi_ws.LOBBY.queue == []


def test_room_tells_each_member_which_entry_is_theirs(server, outbox):
    host = connect(server, account(outbox, 1), 1)
    guest = connect(server, account(outbox, 2), 2)
    host.send_json({"t": "room.create"})
    code = until(host, "room")["code"]
    guest.send_json({"t": "room.join", "code": code})
    assert until(guest, "room")["me"] == 1
    assert until(host, "room")["me"] == 0
    host.send_json({"t": "room.leave"})
    left = until(guest, "room")
    assert left["me"] == 0 and left["members"][0]["host"]  # 방장 승계를 내 칸으로 안다


def test_deeply_nested_json_is_a_bad_message(server, outbox):
    w = connect(server, account(outbox, 1))
    w.send_text("[" * 2048)  # 2KB를 꽉 채운 중첩 — 연결은 유지되고 bad_message만
    assert until(w, "error")["code"] == "bad_message"
    w.send_json({"t": "ping"})
    assert until(w, "pong") == {"t": "pong"}


def test_status_query_in_room_answers_only_the_asker(server, outbox):
    host = connect(server, account(outbox, 1), 1)
    guest = connect(server, account(outbox, 2), 2)
    host.send_json({"t": "room.create"})
    code = until(host, "room")["code"]
    guest.send_json({"t": "room.join", "code": code})
    until(guest, "room")
    until(host, "room")
    for _ in range(3):
        guest.send_json({"t": "unqueue"})
        assert until(guest, "room")["me"] == 1
    host.send_json({"t": "ping"})
    assert host.receive_json() == {"t": "pong"}  # 방장에게 방 상태가 다시 쌓이지 않았다


def test_backlogged_connection_leaves_queue_at_once(server, outbox, monkeypatch):
    """보내기가 밀려 닫히는 연결은 닫힘을 기다리지 않고 대기열에서 빠진다(그사이 매칭에 끼지 않게)."""
    monkeypatch.setattr(multi_ws, "BACKLOG", 0)  # 다음 보내기에서 바로 '밀림'
    t = account(outbox, 1)
    w = server.opened.enter_context(server.websocket_connect("/api/ws"))
    w.send_json({"t": "auth", "token": t})
    assert closed_with(w) == 1011  # 첫 'lobby' 알림부터 밀려 닫힘
    assert 1 not in {p.account for p in multi_ws.LOBBY.queue} and not multi_ws.CONNS


def test_host_dropped_mid_broadcast_new_host_ends_with_me_zero(server, outbox, monkeypatch):
    """방 알림을 보내다 방장 연결이 밀려 닫혀도, 남은 사람이 마지막에 받는 방 상태는 새 구성(me=0, 방장)."""
    host = connect(server, account(outbox, 1), 1)
    guest = connect(server, account(outbox, 2), 2)
    host.send_json({"t": "room.create"})
    code = until(host, "room")["code"]
    guest.send_json({"t": "room.join", "code": code})
    until(guest, "room")
    until(host, "room")
    real, host_id, fired = multi_ws.send, multi_ws.LOBBY.rooms[code].members[0].account, []

    def flaky(account, msg):  # 방장에게 보내는 다음 방 알림 한 번만 '밀림'
        if account == host_id and msg["t"] == "room" and not fired:
            fired.append(1)
            multi_ws._drop(account, multi_ws.CONNS[account], 1011)
            return
        real(account, msg)

    monkeypatch.setattr(multi_ws, "send", flaky)
    third = connect(server, account(outbox, 3), 3)
    third.send_json({"t": "room.join", "code": code})
    final = [{"nick": "p2", "host": True}, {"nick": "p3", "host": False}]

    def last_room(w):  # 밀리기 전 구성의 알림이 먼저 올 수 있다 — 새 구성 알림 뒤에는 옛 알림이 더 오면 안 된다
        while (m := until(w, "room"))["members"] != final:
            pass
        w.send_json({"t": "ping"})
        assert w.receive_json() == {"t": "pong"}
        return m

    assert last_room(guest)["me"] == 0
    assert last_room(third)["me"] == 1


def test_connection_closed_for_flooding_leaves_queue_before_close_finishes(server, outbox, monkeypatch):
    left_before_close = []
    real_close = multi_ws._close

    async def slow_close(ws, code):
        left_before_close.append(not multi_ws.LOBBY.queue)
        await real_close(ws, code)

    monkeypatch.setattr(multi_ws, "_close", slow_close)
    w = connect(server, account(outbox, 1))
    w.send_json({"t": "queue"})
    until(w, "queued")
    for _ in range(12):
        w.send_json({"t": "ping"})
    assert closed_with(w) == 1008
    assert left_before_close == [True]  # 닫기 전에 이미 대기열에서 빠져 있었다


def test_deferred_room_notice_skips_a_room_already_removed(server, outbox):
    """밀린 연결 정리의 방 알림이 미뤄진 사이 방이 정리되면(30분) 남은 사람은 lobby 뒤에 옛 방을 받지 않는다."""
    host = connect(server, account(outbox, 1), 1)
    guest = connect(server, account(outbox, 2), 2)
    host.send_json({"t": "room.create"})
    code = until(host, "room")["code"]
    guest.send_json({"t": "room.join", "code": code})
    until(guest, "room")
    until(host, "room")
    lb = multi_ws.LOBBY

    async def race():  # 같은 루프에서: 방장 밀림(알림 미룸) → 바로 방 정리 → lobby 알림
        multi_ws._drop(lb.rooms[code].members[0].account, multi_ws.CONNS[lb.rooms[code].members[0].account], 1011)
        for a in lb.sweep(10**12):
            multi_ws.send(a, {"t": "lobby"})

    server.portal.call(race)
    assert until(guest, "lobby") == {"t": "lobby"}
    guest.send_json({"t": "ping"})
    assert guest.receive_json() == {"t": "pong"}  # 옛 방 알림이 끼지 않았다


def test_deferred_disconnect_notice_skips_finished_game(server, outbox, monkeypatch):
    """끊김 알림이 미뤄진 사이 판이 끝나고 친구방으로 옮긴 사람은 방 알림 뒤에 옛 판 상태를 받지 않는다."""
    monkeypatch.setattr(multi_ws, "clock", lambda: 1000.0)
    ws = [connect(server, account(outbox, n), n) for n in range(4)]
    for w in ws:
        w.send_json({"t": "queue"})
    states = [until(w, "state") for w in ws]
    lb = multi_ws.LOBBY
    t = lb.tables[states[0]["id"]]
    dropped = t.accounts[3]
    survivor = next(i for i, s in enumerate(states) if s["seat"] == 0)

    async def race():  # 같은 루프에서: 한 명 밀림(알림 미룸) → 판 끝 → 남은 사람이 방을 만듦
        multi_ws._drop(dropped, multi_ws.CONNS[dropped], 1011)
        t.game.hands[0], t.game.winner, t.finished_at = [], 0, 1000.0  # 0번 자리가 손패를 다 털고 1등
        multi_ws._handle(t.accounts[0], multi_ws.Player(t.accounts[0], "x"), {"t": "room.create"})

    server.portal.call(race)
    w = ws[survivor]
    while (m := w.receive_json())["t"] != "room":
        pass
    w.send_json({"t": "ping"})
    assert w.receive_json() == {"t": "pong"}  # 방 알림 뒤에 옛 판 상태가 끼지 않았다


def test_late_move_for_an_old_turn_is_rejected(server, outbox, monkeypatch):
    """A의 패스가 늦게 오는 사이 자동 패스·남의 수가 지나가 다시 A 차례가 돼도, 옛 번호(ply)의 수는 거부."""
    now = [1000.0]
    monkeypatch.setattr(multi_ws, "clock", lambda: now[0])
    ws = [connect(server, account(outbox, n), n) for n in range(4)]
    for w in ws:
        w.send_json({"t": "queue"})
    states = [until(w, "state") for w in ws]
    me = next(i for i, s in enumerate(states) if s["seat"] == s["turn"])
    old_ply = states[me]["ply"]
    t = multi_ws.LOBBY.tables[states[0]["id"]]
    for _ in range(4):  # 네 자리 모두 시간 초과 → 다시 me 차례(선이 바뀌지 않게 패스만)
        now[0] = t.deadline
        server.portal.call(_tick_once)
    assert t.game.turn == states[me]["seat"] and t.ply != old_ply
    ws[me].send_json({"t": "move", "game": states[me]["id"], "ply": old_ply, "tiles": []})
    assert until(ws[me], "error")["code"] == "not_your_turn"
    ws[me].send_json({"t": "move", "game": states[me]["id"], "tiles": []})
    assert until(ws[me], "error") == {"t": "error", "code": "illegal", "reason": "bad_ply"}


async def _tick_once():
    for t in list(multi_ws.LOBBY.tables.values()):
        if ev := t.tick(multi_ws.clock()):
            multi_ws.push(t, ev)


def test_bad_signature_token_never_touches_db(server, monkeypatch):
    called = []
    monkeypatch.setattr(multi_ws.web, "socket_session", lambda token: called.append(token))
    with server.websocket_connect("/api/ws") as w:
        w.send_json({"t": "auth", "token": "not.a.jwt"})
        assert closed_with(w) == 4401
    assert called == []


def test_expired_token_cannot_act_even_before_close(server, outbox, monkeypatch):
    w = connect(server, account(outbox, 1), 1)
    monkeypatch.setattr(multi_ws.time, "time", lambda: 10**10)  # 시계를 토큰 만료 뒤로 — 닫히기 전 틈에 보낸 수
    w.send_json({"t": "queue"})
    assert closed_with(w) == 4401  # 처리하지 않고(만료 연결엔 오류 알림도 안 보냄) 닫힌다
    assert multi_ws.LOBBY.queue == []


def test_token_expiry_during_slow_recheck_closes_at_expiry(server, outbox, monkeypatch):
    """재확인 DB 조회가 늦는 사이 토큰이 만료되면 조회를 기다리지 않고 만료 때 닫힌다."""
    import time

    monkeypatch.setattr(sessions, "ACCESS_TTL", 2)
    monkeypatch.setattr(multi_ws, "RECHECK", 0.2)
    monkeypatch.setattr(multi_ws, "AUTH_WAIT", 30)  # 5초 제한이 아니라 만료 때문에 닫히는지 보려고
    w = connect(server, account(outbox, 1), 1)
    monkeypatch.setattr(multi_ws.web, "socket_alive", lambda s: time.sleep(10) or True)
    start = time.perf_counter()
    assert closed_with(w) == 4401
    assert time.perf_counter() - start < 4


def test_server_asks_to_renew_before_expiry(server, outbox, monkeypatch):
    monkeypatch.setattr(sessions, "ACCESS_TTL", 3)
    monkeypatch.setattr(multi_ws, "RENEW_AHEAD", 2)
    w = connect(server, account(outbox, 1), 1)
    assert w.receive_json() == {"t": "renew"}  # 만료 2초 전 안내(아직 닫히지 않음)
    w.send_json({"t": "ping"})
    assert until(w, "pong") == {"t": "pong"}


def test_connecting_with_nearly_expired_token_gets_renew_at_once(server, outbox, monkeypatch):
    monkeypatch.setattr(sessions, "ACCESS_TTL", 30)
    monkeypatch.setattr(multi_ws, "RENEW_AHEAD", 60)  # 이미 안내 구간
    w = connect(server, account(outbox, 1), 1)
    assert w.receive_json() == {"t": "renew"}


def test_renewal_during_slow_recheck_keeps_connection(server, outbox, monkeypatch):
    """재확인 조회가 늦는 사이 갱신하면, 처음 만료 시각을 지나도 닫지 않는다.
    만료 시각은 초 단위 내림이라: 처음 만료 ≤ 시작+6초, 3초 뒤 갱신한 만료 ≥ 시작+8초 → 7초에 확인."""
    import time

    monkeypatch.setattr(sessions, "ACCESS_TTL", 6)
    monkeypatch.setattr(multi_ws, "RECHECK", 0.2)
    monkeypatch.setattr(multi_ws, "RENEW_AHEAD", 0)
    monkeypatch.setattr(multi_ws, "AUTH_WAIT", 30)  # 5초 조회 제한이 아니라 만료 판단만 보려고
    signed_up(browser(), outbox, email="q@x.com", nick="quicker")
    app_client = TestClient(app, base_url=ORIGIN, headers=APP)
    tokens = login(app_client, email="q@x.com").json()
    start = time.time()
    w = connect(server, tokens["access"], 1)
    monkeypatch.setattr(multi_ws.web, "socket_alive", lambda s: time.sleep(9) or True)  # 처음 만료를 넘기는 조회
    time.sleep(max(start + 3 - time.time(), 0))
    fresh = app_client.post("/api/auth/refresh", json={"refresh": tokens["refresh"]}).json()["access"]
    w.send_json({"t": "auth", "token": fresh})
    time.sleep(max(start + 7 - time.time(), 0))  # 처음 토큰 만료 지남, 조회는 아직 진행 중
    w.send_json({"t": "ping"})
    assert until(w, "pong") == {"t": "pong"}


def test_token_expiring_during_auth_lookup_is_refused(server, outbox, monkeypatch):
    import time

    monkeypatch.setattr(sessions, "ACCESS_TTL", 1)
    t = account(outbox, 1)
    real = multi_ws.web.socket_session
    monkeypatch.setattr(multi_ws.web, "socket_session", lambda token: time.sleep(2.1) or real(token))  # 조회 중 만료
    with server.websocket_connect("/api/ws") as w:
        w.send_json({"t": "auth", "token": t})
        assert closed_with(w) == 4401
    assert not multi_ws.CONNS


def test_expired_queued_player_is_not_matched(server, outbox, monkeypatch):
    """감시 작업이 늦어 만료된 대기자가 아직 안 닫혔어도, 네 번째가 들어올 때 그 사람은 판에 안 들어간다."""
    import time

    async def lagging_watch(ws, s):  # 감시 작업이 닫기 전 틈을 흉내
        await asyncio.sleep(3600)

    monkeypatch.setattr(multi_ws, "_watch", lagging_watch)
    monkeypatch.setattr(multi_ws, "RATE", 1000)
    monkeypatch.setattr(sessions, "ACCESS_TTL", 3)  # 만료 시각은 초 단위 내림 — 최소 2초는 남게
    stale_token = account(outbox, 1)
    stale = connect(server, stale_token, 1)
    monkeypatch.setattr(sessions, "ACCESS_TTL", 900)
    others = [connect(server, account(outbox, n), n) for n in (2, 3, 4, 5)]
    stale.send_json({"t": "queue"})
    until(stale, "queued")
    for w in others[:2]:
        w.send_json({"t": "queue"})
        until(w, "queued")
    time.sleep(max(sessions.decode(stale_token)["exp"] - time.time() + 0.1, 0))  # stale 토큰 만료
    others[2].send_json({"t": "queue"})
    assert closed_with(stale) == 4401
    assert multi_ws.LOBBY.tables == {}  # 셋만 남아 판이 안 열림
    others[3].send_json({"t": "queue"})
    assert until(others[3], "state")["t"] == "state"
    (t,) = multi_ws.LOBBY.tables.values()
    assert len(t.accounts) == 4 and all(a in multi_ws.CONNS for a in t.accounts)  # 닫힌 stale은 없다


def test_expired_player_in_game_gets_no_more_state(server, outbox, monkeypatch):
    """감시 작업보다 타이머가 먼저 돌아도, 만료된 연결에는 새 판 상태(손패)를 보내지 않고 닫는다."""
    import time

    async def lagging_watch(ws, s):
        await asyncio.sleep(3600)

    now = [1000.0]
    monkeypatch.setattr(multi_ws, "clock", lambda: now[0])
    monkeypatch.setattr(multi_ws, "_watch", lagging_watch)
    monkeypatch.setattr(sessions, "ACCESS_TTL", 3)
    stale_token = account(outbox, 0)
    monkeypatch.setattr(sessions, "ACCESS_TTL", 900)
    ws = [connect(server, stale_token, 0)] + [connect(server, account(outbox, n), n) for n in (1, 2, 3)]
    for w in ws:
        w.send_json({"t": "queue"})
    start = [until(w, "state") for w in ws]
    time.sleep(max(sessions.decode(stale_token)["exp"] - time.time() + 0.1, 0))
    now[0] = start[0]["deadline"]  # 타이머가 패스하고 모두에게 상태를 보낸다
    for w in ws[1:]:
        until(w, "state")
    got = []
    with pytest.raises(WebSocketDisconnect) as e:
        while True:
            got.append(ws[0].receive_json())
    assert e.value.code == 4401 and not any(m.get("t") == "state" for m in got)


def test_renewal_follows_raised_auth_version(server, outbox, monkeypatch):
    """세션은 그대로 두고 인증 버전만 오르는 경우(이메일 변경) — 갱신한 토큰으로 이어 가면 재확인에서 안 끊긴다."""
    import time

    monkeypatch.setattr(multi_ws, "RENEW_AHEAD", 0)
    monkeypatch.setattr(multi_ws, "RECHECK", 1.5)  # 첫 재확인은 연결 1.5초 뒤 — 그 전에 버전 올림·갱신을 끝낸다
    signed_up(browser(), outbox, email="v@x.com", nick="versioned")
    app_client = TestClient(app, base_url=ORIGIN, headers=APP)
    tokens = login(app_client, email="v@x.com").json()
    start = time.monotonic()
    w = connect(server, tokens["access"], 1)
    with db.tx() as c:
        c.execute("UPDATE accounts SET auth_version = auth_version + 1 WHERE email = %s", ("v@x.com",))
    fresh = app_client.post("/api/auth/refresh", json={"refresh": tokens["refresh"]}).json()["access"]
    w.send_json({"t": "auth", "token": fresh})
    w.send_json({"t": "ping"})
    until(w, "pong")
    assert time.monotonic() - start < 1.5  # 재확인 전에 갱신까지 끝났다
    time.sleep(2.5)  # 재확인 한 번 이상
    w.send_json({"t": "ping"})
    assert until(w, "pong") == {"t": "pong"}
