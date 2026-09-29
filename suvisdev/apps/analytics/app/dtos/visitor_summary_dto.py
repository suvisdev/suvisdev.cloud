from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DailyVisitorCountDto:
    date: date
    count: int  # 사람(is_bot=false)
    bots: int = 0
    one_shot: int = 0  # 사람 중 핑 1회(60초 안에 이탈)


@dataclass(frozen=True)
class VisitorSummaryDto:
    now_active: int
    today: int  # 사람
    today_bots: int
    today_one_shot: int
    last_7_days_total: int
    cumulative_total: int
    last_7_days_series: tuple[DailyVisitorCountDto, ...]
