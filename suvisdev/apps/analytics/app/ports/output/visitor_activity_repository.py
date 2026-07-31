from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from analytics.app.dtos.visitor_summary_dto import DailyVisitorCountDto


class VisitorActivityRepository(ABC):
    @abstractmethod
    async def upsert_visit(self, visitor_id: str, visit_date: date, now: datetime) -> None: ...

    @abstractmethod
    async def count_active_since(self, since: datetime) -> int: ...

    @abstractmethod
    async def count_unique_on(self, visit_date: date) -> int: ...

    @abstractmethod
    async def daily_counts_since(self, start_date: date) -> list[DailyVisitorCountDto]: ...

    @abstractmethod
    async def count_unique_total(self) -> int: ...
