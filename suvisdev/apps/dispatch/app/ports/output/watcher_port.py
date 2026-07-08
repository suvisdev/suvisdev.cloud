from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.app.dtos.watcher_dto import WatcherIntroduceQuery, WatcherIntroduceResponse


class WatcherPort(ABC):
    @abstractmethod
    async def introduce_myself(self, query: WatcherIntroduceQuery) -> WatcherIntroduceResponse: ...
