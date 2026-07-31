from __future__ import annotations

from abc import ABC, abstractmethod

from analytics.app.dtos.visitor_summary_dto import VisitorSummaryDto


class GetVisitorSummaryUseCase(ABC):
    @abstractmethod
    async def summary(self) -> VisitorSummaryDto: ...
