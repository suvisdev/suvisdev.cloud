from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class VisitPingRequestSchema(BaseModel):
    visitor_id: str


class DailyVisitorCountSchema(BaseModel):
    date: date
    count: int
    bots: int = 0
    one_shot: int = 0


class VisitorSummarySchema(BaseModel):
    now_active: int
    today: int
    today_bots: int = 0
    today_one_shot: int = 0
    last_7_days_total: int
    cumulative_total: int
    last_7_days_series: list[DailyVisitorCountSchema]
