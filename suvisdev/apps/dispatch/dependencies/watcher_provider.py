from __future__ import annotations

from fastapi import Depends

from dispatch.adapter.outbound.llm.kor_unsmile_moderation_adapter import (
    KorUnsmileModerationAdapter,
)
from dispatch.adapter.outbound.repositories.watcher_repository import WatcherRepository
from dispatch.app.ports.input.watcher_use_case import WatcherUseCase
from dispatch.app.ports.output.moderation_port import ModerationPort
from dispatch.app.ports.output.watcher_port import WatcherPort
from dispatch.app.use_cases.watcher_interactor import WatcherInteractor


def get_watcher_repository() -> WatcherPort:
    return WatcherRepository()


def get_watcher_moderation_port() -> ModerationPort:
    return KorUnsmileModerationAdapter()


def get_watcher_use_case(
    repository: WatcherPort = Depends(get_watcher_repository),
    moderation: ModerationPort = Depends(get_watcher_moderation_port),
) -> WatcherUseCase:
    return WatcherInteractor(repository=repository, moderation=moderation)
