from __future__ import annotations

from dispatch.app.dtos.watcher_dto import WatcherIntroduceQuery, WatcherIntroduceResponse
from dispatch.app.ports.output.watcher_port import WatcherPort


class WatcherRepository(WatcherPort):
    async def introduce_myself(self, query: WatcherIntroduceQuery) -> WatcherIntroduceResponse:
        return WatcherIntroduceResponse(id=query.id, name=query.name)
