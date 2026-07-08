from __future__ import annotations

from abc import ABC, abstractmethod

from silicon_valley.app.dtos.piper_gilfoyle_sys_dto import GilfoyleSysQuery, GilfoyleSysResponse


class GilfoyleSysPort(ABC):
    """piper_gilfoyle_sys output port."""

    @abstractmethod
    async def introduce_myself(self, query: GilfoyleSysQuery) -> GilfoyleSysResponse:
        pass
