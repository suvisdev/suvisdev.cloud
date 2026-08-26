"""Use Case 단위 테스트용 Fake 포트 구현. 실제 Postgres 없이 로직만 검증한다."""

from __future__ import annotations

from datetime import date, datetime

from analytics.app.dtos.visitor_summary_dto import DailyVisitorCountDto
from analytics.app.ports.output.visitor_activity_repository import VisitorActivityRepository


class _FakeVisitorActivityRepository(VisitorActivityRepository):
    def __init__(self) -> None:
        # (visitor_id, visit_date) -> (first_seen_at, last_seen_at)
        self.rows: dict[tuple[str, date], tuple[datetime, datetime]] = {}

    async def upsert_visit(self, visitor_id: str, visit_date: date, now: datetime) -> None:
        key = (visitor_id, visit_date)
        if key in self.rows:
            first_seen_at, _ = self.rows[key]
            self.rows[key] = (first_seen_at, now)
        else:
            self.rows[key] = (now, now)

    async def count_active_since(self, since: datetime) -> int:
        visitors = {
            vid for (vid, _), (_, last_seen_at) in self.rows.items() if last_seen_at >= since
        }
        return len(visitors)

    async def count_unique_on(self, visit_date: date) -> int:
        visitors = {vid for (vid, d) in self.rows if d == visit_date}
        return len(visitors)

    async def daily_counts_since(self, start_date: date) -> list[DailyVisitorCountDto]:
        by_date: dict[date, set[str]] = {}
        for vid, d in self.rows:
            if d >= start_date:
                by_date.setdefault(d, set()).add(vid)
        return [
            DailyVisitorCountDto(date=d, count=len(visitors))
            for d, visitors in sorted(by_date.items())
        ]

    async def count_unique_total(self) -> int:
        return len({vid for vid, _ in self.rows})
