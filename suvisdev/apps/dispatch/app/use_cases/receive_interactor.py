from __future__ import annotations

import asyncio
import logging

from dispatch.app.dtos.receive_dto import ReceiveItem, ReceiveSaveCommand
from dispatch.app.ports.input.receive_use_case import ReceiveUseCase
from dispatch.app.ports.input.watcher_use_case import WatcherUseCase
from dispatch.app.ports.output.dispatch_errors import DispatchError
from dispatch.app.ports.output.embedding_port import EmbeddingPort
from dispatch.app.ports.output.receive_port import ReceivePort

logger = logging.getLogger(__name__)


class ReceiveInteractor(ReceiveUseCase):
    def __init__(
        self,
        *,
        repository: ReceivePort,
        embedding: EmbeddingPort,
        watcher: WatcherUseCase,
    ) -> None:
        self._repository = repository
        self._embedding = embedding
        self._watcher = watcher

    async def save(self, command: ReceiveSaveCommand) -> ReceiveItem:
        text = f"{command.subject}\n{command.body}"
        is_clean = await asyncio.to_thread(self._watcher.filter_stop_word, text)
        if not is_clean:
            raise DispatchError("비속어가 감지되어 메일을 저장하지 않았습니다.", status_code=422)
        vector = await self._embed_or_none(command)
        return await self._repository.save(command, vector)

    async def _embed_or_none(self, command: ReceiveSaveCommand) -> list[float] | None:
        text = f"{command.subject}\n\n{command.body}".strip()
        if not text:
            return None
        try:
            return await self._embedding.embed(text)
        except DispatchError as e:
            # Ollama 장애로 임베딩이 실패해도 실제 수신 메일 데이터는 유실시키지 않는다.
            logger.warning(
                f"[ReceiveInteractor] 임베딩 생성 실패, embedding 없이 저장 | detail={e.detail}"
            )
            return None

    async def list_all(self, limit: int) -> list[ReceiveItem]:
        return await self._repository.list_all(limit)

    async def delete(self, item_id: int) -> None:
        await self._repository.delete(item_id)
