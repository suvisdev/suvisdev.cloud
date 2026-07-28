from __future__ import annotations

from abc import ABC, abstractmethod

from execsuite.app.dtos.piper_dinesh_dash_dto import DineshDashQuery, DineshDashResponse


class DineshDashPort(ABC):
    """piper_dinesh_dash output port."""

    @abstractmethod
    async def introduce_myself(self, query: DineshDashQuery) -> DineshDashResponse:
        pass
