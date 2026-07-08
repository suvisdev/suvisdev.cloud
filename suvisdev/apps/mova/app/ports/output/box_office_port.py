"""박스오피스 Output Port — KOFIC 어댑터가 구현한다."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_box_office_dto import BoxOfficeEntryDto


class BoxOfficePort(ABC):
    @abstractmethod
    async def fetch_box_office(
        self, target_date: str | None, week_gb: str
    ) -> list[BoxOfficeEntryDto]:
        """주간 박스오피스 순위 조회 (target_date 없으면 전일 기준)."""
