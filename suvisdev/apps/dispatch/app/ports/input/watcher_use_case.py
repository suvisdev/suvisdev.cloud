from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.adapter.inbound.api.schemas.watcher_schema import WatcherIntroduceSchema
from dispatch.app.dtos.watcher_dto import WatcherIntroduceResponse


class WatcherUseCase(ABC):
    @abstractmethod
    async def introduce_myself(
        self, schema: WatcherIntroduceSchema
    ) -> WatcherIntroduceResponse: ...

    @abstractmethod
    def filter_stop_word(self, text: str) -> bool:
        """비속어 필터링. 정상 텍스트면 True, 비속어 감지 시 False."""
