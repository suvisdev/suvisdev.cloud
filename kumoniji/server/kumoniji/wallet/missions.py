"""일일 미션(11-24 사용자 확정 10개, 5개 완료). 하루는 한국 시간 자정 기준. 순수 함수."""

from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
MISSIONS = ["games5", "games10", "wins2", "low3", "five3", "triple2", "today", "score30", "oddeven", "fullhouse"]
NEED = {
    "games5": ("games", 5),
    "games10": ("games", 10),
    "wins2": ("wins", 2),
    "low3": ("low3", 1),
    "five3": ("five", 3),
    "triple2": ("triple", 2),
    "today": ("today", 1),
    "score30": ("score", 30),
    "oddeven": ("oddeven", 1),
    "fullhouse": ("fullhouse", 1),
}


def day_of(ts: float) -> str:
    return datetime.fromtimestamp(ts, KST).date().isoformat()


def add_game(c: dict, seat_stats: dict, rank: int, left: int, points: int) -> dict:
    """그날 누적(c)에 한 판을 더한 새 dict."""
    out = dict(c)
    add = {**seat_stats, "games": 1, "wins": int(rank == 1), "low3": int(left <= 3), "score": max(points, 0)}
    for k, v in add.items():
        out[k] = out.get(k, 0) + v
    return out


def done(c: dict) -> list[str]:
    return [m for m in MISSIONS if c.get(NEED[m][0], 0) >= NEED[m][1]]
