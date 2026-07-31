from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from analytics.app.dtos.visitor_summary_dto import VisitorSummaryDto
from analytics.app.ports.input.get_visitor_summary_use_case import GetVisitorSummaryUseCase
from analytics.app.ports.output.visitor_activity_repository import VisitorActivityRepository

_KST = ZoneInfo("Asia/Seoul")
_ACTIVE_WINDOW = timedelta(minutes=2)
_SERIES_DAYS = 7


class GetVisitorSummaryInteractor(GetVisitorSummaryUseCase):
    def __init__(self, *, repository: VisitorActivityRepository) -> None:
        self._repository = repository

    async def summary(self) -> VisitorSummaryDto:
        now = datetime.now(UTC)
        today_kst = now.astimezone(_KST).date()
        start_date = today_kst - timedelta(days=_SERIES_DAYS - 1)

        now_active = await self._repository.count_active_since(now - _ACTIVE_WINDOW)
        today_count = await self._repository.count_unique_on(today_kst)
        series = await self._repository.daily_counts_since(start_date)
        cumulative_total = await self._repository.count_unique_total()

        return VisitorSummaryDto(
            now_active=now_active,
            today=today_count,
            last_7_days_total=sum(d.count for d in series),
            cumulative_total=cumulative_total,
            last_7_days_series=tuple(series),
        )
