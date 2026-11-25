from kumoniji.wallet import missions

S0 = {"five": 0, "triple": 0, "oddeven": 0, "fullhouse": 0, "today": 0}


def test_day_is_korean_midnight():
    assert missions.day_of(1764514799) == "2025-11-30"  # 2025-11-30 23:59:59 KST
    assert missions.day_of(1764514800) == "2025-12-01"  # 2025-12-01 00:00:00 KST(UTC로는 11-30 15:00)


def test_missions_need_their_counts():
    c = {}
    for _ in range(4):
        c = missions.add_game(c, S0, rank=2, left=5, points=-3)
    assert missions.done(c) == []
    c = missions.add_game(c, S0 | {"five": 3, "triple": 2, "today": 1, "oddeven": 1, "fullhouse": 1}, rank=1, left=0, points=31)
    assert missions.done(c) == ["games5", "low3", "five3", "triple2", "today", "score30", "oddeven", "fullhouse"]
    c = missions.add_game(c, S0, rank=1, left=0, points=1)
    assert "wins2" in missions.done(c)
