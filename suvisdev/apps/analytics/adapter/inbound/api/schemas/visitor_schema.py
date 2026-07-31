from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class VisitPingRequestSchema(BaseModel):
    visitor_id: str


class DailyVisitorCountSchema(BaseModel):
    date: date
    count: int


class VisitorSummarySchema(BaseModel):
    now_active: int
    today: int
    last_7_days_total: int
    cumulative_total: int
    last_7_days_series: list[DailyVisitorCountSchema]
