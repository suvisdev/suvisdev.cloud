from __future__ import annotations

from abc import ABC, abstractmethod

from execsuite.app.dtos.piper_bighetti_hr_dto import BighettiHrQuery, BighettiHrResponse


class BighettiHrPort(ABC):
    """piper_bighetti_hr output port."""

    @abstractmethod
    async def introduce_myself(self, query: BighettiHrQuery) -> BighettiHrResponse:
        pass
