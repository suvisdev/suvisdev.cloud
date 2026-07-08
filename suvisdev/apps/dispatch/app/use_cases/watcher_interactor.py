from __future__ import annotations

from dispatch.adapter.inbound.api.schemas.watcher_schema import WatcherIntroduceSchema
from dispatch.app.dtos.watcher_dto import WatcherIntroduceQuery, WatcherIntroduceResponse
from dispatch.app.ports.input.watcher_use_case import WatcherUseCase
from dispatch.app.ports.output.moderation_port import ModerationPort
from dispatch.app.ports.output.watcher_port import WatcherPort


class WatcherInteractor(WatcherUseCase):
    def __init__(self, *, repository: WatcherPort, moderation: ModerationPort) -> None:
        self._repository = repository
        self._moderation = moderation

    async def introduce_myself(self, schema: WatcherIntroduceSchema) -> WatcherIntroduceResponse:
        return await self._repository.introduce_myself(
            WatcherIntroduceQuery(id=schema.id, name=schema.name)
        )

    def filter_stop_word(self, text: str) -> bool:
        """비속어 필터링 — KcELECTRA-base 임베딩 유사도 기반. CPU/GPU-bound라 sync."""
        return self._moderation.is_clean(text)
