from __future__ import annotations

from abc import ABC, abstractmethod

from execsuite.app.dtos.piper_hendricks_ceo_dto import HendricksCeoQuery, HendricksCeoResponse


class HendricksCeoPort(ABC):
    """piper_hendricks_ceo output port."""

    @abstractmethod
    async def introduce_myself(self, query: HendricksCeoQuery) -> HendricksCeoResponse:
        pass
