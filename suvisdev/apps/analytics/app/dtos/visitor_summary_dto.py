from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DailyVisitorCountDto:
    date: date
    count: int


@dataclass(frozen=True)
class VisitorSummaryDto:
    now_active: int
    today: int
    last_7_days_total: int
    cumulative_total: int
    last_7_days_series: tuple[DailyVisitorCountDto, ...]
