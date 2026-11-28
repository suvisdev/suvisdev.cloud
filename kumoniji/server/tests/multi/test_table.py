import random

import pytest

from kumoniji.multi.table import GONE, KEEP, TURN, Illegal, MultiTable, NotYourTurn
from kumoniji.view import enc, legal_moves

ACC = [11, 22, 33, 44]


def table(seed=1, now=1000.0):
    return MultiTable(ACC, ["a", "b", "c", "d"], now, random.Random(seed))


def test_state_hides_playable_hints():
    """멀티는 낼 수 있는 패를 알려 주지 않는다(싱글 연습만, 11-27 사용자)."""
    t = table()
    for seat in range(4):
        st = t.state(seat, [])
        assert "moves" not in st and "playable" not in st


def test_state_shows_only_my_hand():
    t = table()
    for seat in range(4):
        s = t.state(seat, [])
        mine = {enc(x) for x in t.game.hands[seat]}
        others = {enc(x) for i, h in enumerate(t.game.hands) if i != seat for x in h}
        assert set(s["hand"]) == mine
        assert not others & set(str(s).replace("'", " ").split())  # 남의 타일 코드는 어디에도 없다
        assert s["seat"] == seat and s["names"] == ["a", "b", "c", "d"]


def test_timeout_auto_passes_after_20s_only():
    t = table()
    turn = t.game.turn
    assert t.tick(1000 + TURN - 1) == []
    ev = t.tick(1000 + TURN)
    assert ev[0] == {"seat": turn, "tiles": None}
    assert t.game.turn == (turn + 1) % 4  # 선의 패스도 차례만 넘긴다(계획 A)
    assert t.deadline == 1000 + 2 * TURN


def test_move_resets_deadline_and_checks_turn():
    t = table()
    seat = t.game.turn
    other = ACC[(seat + 1) % 4]
    with pytest.raises(NotYourTurn):
        t.move(other, [], 1005)
    with pytest.raises(NotYourTurn):
        t.move(999, [], 1005)  # 판에 없는 계정
    low = enc(t.game.hands[seat][0])
    ev = t.move(ACC[seat], [low], 1010)
    assert ev[0] == {"seat": seat, "tiles": [low]}
    assert t.deadline == 1010 + TURN


def test_illegal_move_reports_reason():
    t = table()
    seat = t.game.turn
    foreign = enc(t.game.hands[(seat + 1) % 4][0])
    with pytest.raises(Illegal) as e:
        t.move(ACC[seat], [foreign], 1001)
    assert e.value.code == "not_in_hand"
    with pytest.raises(Illegal) as e:
        t.move(ACC[seat], ["x9"], 1001)
    assert e.value.code == "bad_tile"


def test_all_disconnected_expires_after_3_minutes():
    t = table()
    for a in ACC:
        t.set_connected(a, False, 2000)
    assert not t.expired(2000 + GONE - 1)
    assert t.expired(2000 + GONE)
    t.set_connected(ACC[0], True, 2100)  # 한 명이라도 돌아오면 무효 아님
    assert not t.expired(2000 + GONE + 999)


@pytest.mark.parametrize("seed", range(200))
def test_random_games_finish_without_errors(seed):
    """무작위 합법 수·패스·시간 초과를 섞어 끝까지 — 예외 없이 끝나고 정산 합 0, 끝난 판은 10분 뒤 제거."""
    rng = random.Random(seed)
    t = table(seed)
    now = 1000.0
    for _ in range(2000):
        if t.game.winner is not None:
            break
        seat = t.game.turn
        r = rng.random()
        if r < 0.1:
            now = t.deadline
            t.tick(now)
            continue
        now += rng.random() * 5
        moves = legal_moves(t.game, seat)
        tiles = rng.choice(moves) if moves and r < 0.9 else []
        t.move(ACC[seat], tiles, now)
    assert t.game.winner is not None
    assert sum(t.game.settlement()) == 0
    assert t.state(0, [])["deadline"] is None
    assert not t.expired(t.finished_at + KEEP - 1) and t.expired(t.finished_at + KEEP)


def test_nobody_can_beat_auto_passes_everyone():
    """산13 한 장은 아무도 못 이긴다 → 남은 세 자리를 바로 자동 패스, 바퀴가 끝나 낸 사람이 다시 선."""
    t = table()
    seat, g = t.game.turn, t.game
    top = ("산", 13)
    holder = next(i for i, h in enumerate(g.hands) if top in h)
    if holder != seat:  # 산13을 지금 차례인 자리로 옮긴다(장수는 그대로)
        swap = g.hands[seat][-1]
        g.hands[holder].remove(top)
        g.hands[holder].append(swap)
        g.hands[seat].remove(swap)
        g.hands[seat].append(top)
    ev = t.move(ACC[seat], ["m13"], 1003)
    assert ev == [{"seat": seat, "tiles": ["m13"]}] + [{"seat": (seat + k) % 4, "tiles": None, "auto": True} for k in (1, 2, 3)]
    assert g.turn == seat and g.table == []


def test_late_move_is_rejected_so_timeout_wins():
    t = table()
    seat = t.game.turn
    low = enc(t.game.hands[seat][0])
    with pytest.raises(NotYourTurn):
        t.move(ACC[seat], [low], 1000 + TURN)  # 마감 순간에 온 수
    assert t.tick(1000 + TURN)[0] == {"seat": seat, "tiles": None}


@pytest.mark.parametrize("bad", ["m²", "m" + "9" * 5000, "m0", "m14", "m", "z3", "m+1"])
def test_bad_tile_codes(bad):
    t = table()
    with pytest.raises(Illegal) as e:
        t.move(ACC[t.game.turn], [bad], 1001)
    assert e.value.code == "bad_tile"


def test_state_is_a_snapshot():
    t = table()
    s = t.state(0, [])
    t.set_connected(ACC[1], False, 1001)
    assert s["connected"] == [True] * 4


def test_state_does_not_alias_game_lists():
    t = table()
    s = t.state(0, [])
    t.game.bonus[0] += 5
    t.game.hands[0].clear()
    assert s["bonus"] == [0] * 4 and s["hand"]


def test_expired_table_stays_expired_on_reconnect():
    t = table()
    for a in ACC:
        t.set_connected(a, False, 2000)
    t.set_connected(ACC[0], True, 2000 + GONE)
    assert t.expired(2000 + GONE)


def test_void_table_is_frozen():
    """네 명 모두 끊긴 채 3분 → 무효. 마감이 남아 있어도 수·타이머가 판을 바꾸지 않는다."""
    t = table()
    seat = t.game.turn
    for a in ACC:
        t.set_connected(a, False, 1001)
    late = 1001 + GONE
    t.deadline = late + 100  # 마감 때문이 아니라 무효라서 막히는지 보려고
    before = (t.game.turn, t.game.passes, list(t.game.bonus))
    with pytest.raises(NotYourTurn):
        t.move(ACC[seat], [], late)
    t.deadline = late  # 마감이 지나도 자동 패스 안 함
    assert t.tick(late) == []
    assert (t.game.turn, t.game.passes, list(t.game.bonus)) == before
    assert t.expired(late)


def test_old_tile_spellings_still_decode():
    from kumoniji.view import dec

    assert dec("m01") == dec("m0001") == dec("m1") == dec("m１") == ("산", 1)


def test_gone_since_at_time_zero_is_kept():
    t = table(now=0.0)
    for a in ACC:
        t.set_connected(a, False, 0.0)
    t.set_connected(ACC[0], False, 60.0)  # 중복 끊김 알림
    assert t.expired(GONE)


def test_stale_ply_is_rejected():
    t = table()
    seat = t.game.turn
    with pytest.raises(NotYourTurn):
        t.move(ACC[seat], [], 1001, ply=t.ply + 1)
    t.move(ACC[seat], [], 1001, ply=t.ply)  # 맞는 번호면 받는다


def test_unrevealed_table_is_not_voided_and_reveal_restarts_the_gone_timer():
    """하트를 쓰는 중(공개 전)에는 넷 다 끊겨도 무효로 지우지 않는다 — 지우면 하트만 빠지고 판이 없다(리뷰 지적).
    공개되면 그때부터 GONE초 안에 돌아오면 이어진다."""
    t = MultiTable(ACC, ["a", "b", "c", "d"], 1000.0, random.Random(1), ready=False)
    for a in ACC:
        t.set_connected(a, False, 1000)
    assert not t.void(1000 + GONE * 2) and not t.expired(1000 + GONE * 2)
    t.reveal(1000 + GONE * 2)
    assert not t.void(1000 + GONE * 3 - 1)
    assert t.void(1000 + GONE * 3)


def test_turn_is_15_seconds():
    # 사용자 결정(2026-11-28): 패를 안 내고 15초가 지나면 자동 패스
    assert TURN == 15
