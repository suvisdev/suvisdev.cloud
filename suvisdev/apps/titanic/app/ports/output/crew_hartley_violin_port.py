from __future__ import annotations

from abc import ABC, abstractmethod

from titanic.app.dtos.crew_hartley_violin_dto import HartleyViolinQuery, HartleyViolinResponse


class HartleyViolinPort(ABC):
    """crew_hartley_violin output port."""

    @abstractmethod
    async def introduce_myself(self, query: HartleyViolinQuery) -> HartleyViolinResponse:
        pass
