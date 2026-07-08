from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db
from dispatch.adapter.outbound.llm.ollama_embedding_adapter import OllamaEmbeddingAdapter
from dispatch.adapter.outbound.repositories.receive_repository import ReceiveRepository
from dispatch.app.ports.input.receive_use_case import ReceiveUseCase
from dispatch.app.ports.input.watcher_use_case import WatcherUseCase
from dispatch.app.ports.output.embedding_port import EmbeddingPort
from dispatch.app.ports.output.receive_port import ReceivePort
from dispatch.app.use_cases.receive_interactor import ReceiveInteractor
from dispatch.dependencies.watcher_provider import get_watcher_use_case


def get_receive_repository(session: AsyncSession = Depends(get_db)) -> ReceivePort:
    return ReceiveRepository(session=session)


def get_receive_embedding_port() -> EmbeddingPort:
    return OllamaEmbeddingAdapter()


def get_receive_use_case(
    repository: ReceivePort = Depends(get_receive_repository),
    embedding: EmbeddingPort = Depends(get_receive_embedding_port),
    watcher: WatcherUseCase = Depends(get_watcher_use_case),
) -> ReceiveUseCase:
    return ReceiveInteractor(repository=repository, embedding=embedding, watcher=watcher)
