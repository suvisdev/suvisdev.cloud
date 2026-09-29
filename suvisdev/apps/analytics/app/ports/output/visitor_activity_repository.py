from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from analytics.app.dtos.visitor_summary_dto import DailyVisitorCountDto


class VisitorActivityRepository(ABC):
    @abstractmethod
    async def upsert_visit(
        self,
        visitor_id: str,
        visit_date: date,
        now: datetime,
        *,
        is_bot: bool = False,
        user_agent: str | None = None,
    ) -> None:
        """같은 (visitor_id, visit_date)면 last_seen_at만 갱신 — 봇 판정·UA는 첫 핑 기준."""
        ...

    @abstractmethod
    async def count_active_since(self, since: datetime) -> int: ...

    @abstractmethod
    async def count_unique_on(self, visit_date: date) -> int:
        """사람(is_bot=false) 고유 방문자."""
        ...

    @abstractmethod
    async def count_bots_on(self, visit_date: date) -> int: ...

    @abstractmethod
    async def count_one_shot_on(self, visit_date: date) -> int:
        """사람 중 핑이 한 번뿐(first_seen_at == last_seen_at) — 60초 안에 떠난 접속."""
        ...

    @abstractmethod
    async def daily_counts_since(self, start_date: date) -> list[DailyVisitorCountDto]: ...

    @abstractmethod
    async def count_unique_total(self) -> int: ...
