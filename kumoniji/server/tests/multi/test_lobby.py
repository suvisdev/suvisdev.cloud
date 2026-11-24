import random

import pytest

from kumoniji.multi.lobby import JOIN_FAILS, ROOM_IDLE, Lobby, LobbyError, Player
from kumoniji.multi.table import KEEP


def P(a, ip=None, dev=None):
    return Player(a, f"n{a}", ip or f"ip{a}", f"d{a}" if dev is None else dev)


def lobby():
    return Lobby(random.Random(1))


def test_four_in_queue_make_a_table():
    lb = lobby()
    assert lb.enqueue(P(1), 0) is None
    assert lb.enqueue(P(2), 0) is None
    assert lb.enqueue(P(3), 0) is None
    t = lb.enqueue(P(4), 0)
    assert sorted(t.accounts) == [1, 2, 3, 4] and lb.queue == []
    for a in (1, 2, 3, 4):
        assert lb.table_for(a, 0) is t
    with pytest.raises(LobbyError, match="in_game"):
        lb.enqueue(P(1), 1)


def test_same_ip_or_device_waits_for_next_player():
    lb = lobby()
    lb.enqueue(P(1, ip="home"), 0)
    lb.enqueue(P(2, ip="home"), 0)
    lb.enqueue(P(3), 0)
    assert lb.enqueue(P(4, dev="d3"), 0) is None  # 3과 같은 기기
    assert lb.enqueue(P(5), 0) is None
    t = lb.enqueue(P(6), 0)
    assert sorted(t.accounts) == [1, 3, 5, 6]
    assert [p.account for p in lb.queue] == [2, 4]  # 같은 IP·같은 기기는 다음 판을 기다림


def test_duplicate_and_disconnect_leave_queue():
    lb = lobby()
    lb.enqueue(P(1), 0)
    with pytest.raises(LobbyError, match="in_queue"):
        lb.enqueue(P(1), 0)
    lb.disconnect(1, 0)
    assert lb.queue == []


def test_finished_table_frees_players_and_is_swept():
    lb = lobby()
    for a in (1, 2, 3):
        lb.enqueue(P(a), 0)
    t = lb.enqueue(P(4), 0)
    t.game.winner, t.finished_at = 0, 5.0
    assert lb.table_for(1, 6) is None
    assert lb.enqueue(P(1), 6) is None  # 판마다 새로 매칭
    lb.sweep(5 + KEEP)
    assert t.id not in lb.tables and 2 not in lb.table_of


def test_room_flow():
    lb = lobby()
    r = lb.create_room(P(1), 0)
    assert len(r.code) == 6 and not set(r.code) & set("0O1I")
    for a in (2, 3):
        lb.join_room(P(a, ip="same"), r.code.lower(), 0)  # 친구방은 같은 IP 허용, 소문자 코드도
    with pytest.raises(LobbyError, match="not_host"):
        lb.start_room(2, 0)
    with pytest.raises(LobbyError, match="need_four"):
        lb.start_room(1, 0)
    lb.join_room(P(4, ip="same"), r.code, 0)
    with pytest.raises(LobbyError, match="room_full"):
        lb.join_room(P(5), r.code, 0)
    with pytest.raises(LobbyError, match="in_room"):
        lb.enqueue(P(2), 0)
    t = lb.start_room(1, 0)
    assert sorted(t.accounts) == [1, 2, 3, 4] and r.code not in lb.rooms


def test_host_leaves_next_becomes_host_empty_room_removed():
    lb = lobby()
    r = lb.create_room(P(1), 0)
    lb.join_room(P(2), r.code, 0)
    assert lb.leave_room(1).members[0].account == 2
    lb.disconnect(2, 0)
    assert r.code not in lb.rooms


def test_wrong_codes_are_limited_per_minute():
    lb = lobby()
    r = lb.create_room(P(1), 0)
    for _ in range(JOIN_FAILS):
        with pytest.raises(LobbyError, match="no_room"):
            lb.join_room(P(2), "ZZZZZZ", 10)
    with pytest.raises(LobbyError, match="too_many"):
        lb.join_room(P(2), r.code, 20)  # 맞는 코드도 잠시 막힘
    assert lb.join_room(P(2), r.code, 71).code == r.code


def test_idle_room_removed_after_30_minutes():
    lb = lobby()
    r = lb.create_room(P(1), 0)
    lb.sweep(ROOM_IDLE - 1)
    assert r.code in lb.rooms
    assert lb.sweep(ROOM_IDLE) == [1]  # 방에 있던 사람에게 알린다
    assert r.code not in lb.rooms


def test_unknown_device_is_not_a_conflict():
    lb = lobby()
    for a in (1, 2, 3):
        lb.enqueue(P(a, dev=""), 0)
    assert lb.enqueue(P(4, dev=""), 0) is not None  # 웹(기기 모름)끼리는 IP만 본다


def test_matching_skips_a_blocking_first_player():
    """1번이 2번과 IP, 3번과 기기를 공유 — 앞에서부터 욕심내면 멈추지만 2·3·4·5는 한 판이 된다."""
    lb = lobby()
    lb.enqueue(P(1, ip="A", dev="X"), 0)
    lb.enqueue(P(2, ip="A"), 0)
    lb.enqueue(P(3, dev="X"), 0)
    assert lb.enqueue(P(4), 0) is None
    t = lb.enqueue(P(5), 0)
    assert t is not None and sorted(t.accounts) == [2, 3, 4, 5]
    assert [q.account for q in lb.queue] == [1]


def test_match_found_behind_many_same_ip_players():
    """앞쪽 60명이 같은 IP여도 뒤에 온 서로 다른 세 사람과 한 판(앞쪽에서는 가장 오래 기다린 1명)."""
    lb = lobby()
    for a in range(60):
        lb.enqueue(P(a, ip="cafe"), 0)
    lb.enqueue(P(100), 0)
    lb.enqueue(P(101), 0)
    t = lb.enqueue(P(102), 0)
    assert t is not None and sorted(t.accounts) == [0, 100, 101, 102]


def test_reconnect_updates_queue_ip():
    lb = lobby()
    lb.enqueue(P(1, ip="mobile"), 0)
    assert lb.update(P(1, ip="wifi"), 0) is None
    for a in (2, 3):
        lb.enqueue(P(a), 0)
    assert lb.enqueue(P(4, ip="wifi"), 0) is None  # 1번은 이제 wifi — 같은 IP라 같은 판 안 됨
    t = lb.update(P(4, ip="lte"), 0)  # 4번이 망을 바꾸면 그 자리에서 네 명이 맞춰진다
    assert t is not None and sorted(t.accounts) == [1, 2, 3, 4]
    assert lb.update(P(9), 0) is None  # 대기열에 없는 사람은 그대로


def test_matching_stays_fast_with_crowded_ips():
    """두 IP에 400명이 몰려 네 명을 못 만드는 상황 — 한 번의 입장이 루프를 오래 붙잡지 않는다."""
    import time

    lb = lobby()
    for a in range(400):
        lb.queue.append(P(a, ip="A" if a % 2 else "B"))
    start = time.perf_counter()
    assert lb.enqueue(P(999, ip="C"), 0) is None
    assert time.perf_counter() - start < 0.5  # 고치기 전 1.1초 — 바쁜 CI에서도 흔들리지 않게 넉넉히


def test_same_ip_candidate_with_other_device_is_not_cut():
    """IP A의 앞 넷이 기기 X를 같이 쓰고 다섯째만 Y — B/X·C/Z·D/W와는 A/Y가 짝이다."""
    lb = lobby()
    for a in range(4):
        lb.enqueue(P(a, ip="A", dev="X"), 0)
    lb.enqueue(P(4, ip="A", dev="Y"), 0)
    lb.enqueue(P(5, ip="B", dev="X"), 0)
    lb.enqueue(P(6, ip="C", dev="Z"), 0)
    t = lb.enqueue(P(7, ip="D", dev="W"), 0)
    assert t is not None and sorted(t.accounts) == [4, 5, 6, 7]


def test_db_slot_is_held_until_thread_finishes():
    """시간 초과로 부른 쪽이 취소돼도, 돌고 있는 DB 조회가 끝나기 전엔 자리를 돌려주지 않는다."""
    import asyncio
    import threading

    from kumoniji.multi import ws

    gate = threading.Event()

    async def main():
        ws._slots["auth"] = asyncio.Semaphore(1)
        try:
            await asyncio.wait_for(ws._db("auth", gate.wait), 0.05)
        except TimeoutError:
            pass
        assert ws._slots["auth"].locked()  # 스레드가 아직 돈다 → 자리 그대로
        gate.set()
        await asyncio.sleep(0.1)
        assert not ws._slots["auth"].locked()

    asyncio.run(main())
    ws._slots.clear()


def test_match_found_when_shared_devices_crowd_the_front():
    """앞쪽 200명이 IP는 다르고 기기는 몇 개를 돌려 쓴다 — 그 뒤 IP·기기가 모두 다른 셋과 반드시 매칭되고, 빠르다."""
    import time

    lb = lobby()
    for a in range(200):
        lb.queue.append(P(a, ip=f"x{a}", dev="SAME"))
    lb.queue.append(P(500, ip="y1", dev="u1"))
    lb.queue.append(P(501, ip="y2", dev="u2"))
    start = time.perf_counter()
    t = lb.enqueue(P(502, ip="y3", dev="u3"), 0)
    assert time.perf_counter() - start < 0.5  # 고치기 전 1.1초 — 바쁜 CI에서도 흔들리지 않게 넉넉히
    assert t is not None and len(set(t.accounts) & {500, 501, 502}) == 3


def test_web_player_does_not_collide_with_app_device_named_like_it():
    lb = lobby()
    lb.enqueue(P(1, dev=""), 0)  # 웹
    lb.enqueue(P(2, dev="#1"), 0)  # 앱 기기 값이 우연히 같은 모양
    lb.enqueue(P(3), 0)
    assert lb.enqueue(P(4), 0) is not None


def test_oldest_player_is_kept_when_a_group_with_them_exists():
    """(IP,기기) = (1,A) (2,A) (1,B) (2,C) (3,D) (4,E) — 가장 먼저 온 1번을 넣은 1·4·5·6 조합이 있으니 그걸 고른다."""
    lb = lobby()
    for a, ip, dev in [(1, "1", "A"), (2, "2", "A"), (3, "1", "B"), (4, "2", "C"), (5, "3", "D")]:
        assert lb.enqueue(P(a, ip=ip, dev=dev), 0) is None
    t = lb.enqueue(P(6, ip="4", dev="E"), 0)
    assert t is not None and sorted(t.accounts) == [1, 4, 5, 6]


def test_matching_agrees_with_brute_force():
    """작은 대기열 2,000개를 전부 따져 본 답과 비교 — 조합이 있으면 반드시 찾고, 오래 기다린 순(사전순)으로 가장 앞선 조합."""
    from itertools import combinations

    from kumoniji.multi.lobby import _apart

    rng = random.Random(3)
    for _ in range(2000):
        n = rng.randint(3, 9)
        queue = [P(a, ip=str(rng.randint(0, 3)), dev=rng.choice(["", "X", "Y", "Z", f"u{a}"])) for a in range(n)]
        newcomer = P(99, ip=str(rng.randint(0, 4)), dev=rng.choice(["", "X", f"u99"]))
        ok = [
            c for c in combinations(range(n), 3)
            if all(_apart(x, y) for x, y in combinations([*(queue[i] for i in c), newcomer], 2))
        ]
        lb = lobby()
        lb.queue = list(queue)
        t = lb.enqueue(newcomer, 0)
        if not ok:
            assert t is None
            continue
        best = min(ok)  # 오래 기다린 순으로 가장 앞선 조합
        assert t is not None and sorted(t.accounts) == sorted([99, *(queue[i].account for i in best)])


def test_matching_time_on_random_big_queues():
    import time

    rng = random.Random(5)
    worst = 0.0
    for _ in range(20):
        lb = lobby()
        lb.queue = [P(a, ip=str(rng.randint(0, 2)), dev=rng.choice(["X", "Y", ""])) for a in range(500)]
        start = time.perf_counter()
        lb.enqueue(P(999, ip="9", dev="Q"), 0)
        worst = max(worst, time.perf_counter() - start)
    assert worst < 0.5


def test_matching_fast_when_blocked_candidates_crowd_the_front():
    """앞쪽 2,000명이 같은 IP·기기 묶음 몇 개 — 넣을 수 없는 후보가 몰려도 빠르다(고치기 전 0.38초)."""
    import time

    lb = lobby()
    lb.queue = [P(a, ip=f"s{a % 3}", dev="SAME") for a in range(2000)]
    lb.queue += [P(5000, ip="t1", dev="u1"), P(5001, ip="t2", dev="u2")]
    start = time.perf_counter()
    t = lb.enqueue(P(5002, ip="t3", dev="u3"), 0)
    assert time.perf_counter() - start < 0.2
    assert t is not None and 5000 in t.accounts and 5001 in t.accounts


def test_abandoned_recheck_does_not_run_later():
    """자리를 기다리다 포기한 재확인은 취소된다 — 나중에 자리가 나도 실행되지 않고, 자리 수도 그대로."""
    import asyncio
    import time

    from kumoniji.multi import ws

    ran = []

    async def main():
        ws._slots["recheck"] = asyncio.Semaphore(1)
        await ws._slots["recheck"].acquire()  # 자리가 꽉 참
        orig_alive, orig_wait = ws.web.socket_alive, ws.AUTH_WAIT
        ws.web.socket_alive, ws.AUTH_WAIT = (lambda s: ran.append(1) or True), 0.1
        try:
            assert await ws._recheck({"exp": time.time() + 60}) is False  # 시간 초과로 포기
            ws._slots["recheck"].release()
            await asyncio.sleep(0.2)
        finally:
            ws.web.socket_alive, ws.AUTH_WAIT = orig_alive, orig_wait
        assert ran == [] and not ws._slots["recheck"].locked()

    asyncio.run(main())
    ws._slots.clear()


def test_recheck_retries_when_version_changes_mid_lookup():
    """옛 버전으로 조회하는 사이 갱신해 버전이 오르면, 옛 버전의 실패를 버리고 새 버전으로 다시 본다."""
    import asyncio
    import time

    from kumoniji.multi import ws

    s = {"exp": time.time() + 60, "ver": 1}
    seen = []

    def alive(snap):  # DB에는 버전 2가 맞다. 버전 1 조회 도중 갱신이 들어온다
        seen.append(snap["ver"])
        if snap["ver"] == 1:
            s["ver"] = 2
            return False
        return True

    async def main():
        orig = ws.web.socket_alive
        ws.web.socket_alive = alive
        try:
            assert await ws._recheck(s) is True
        finally:
            ws.web.socket_alive = orig

    asyncio.run(main())
    ws._slots.clear()
    assert seen == [1, 2]
