from __future__ import annotations

from fastapi import APIRouter, Depends

from dispatch.adapter.inbound.api.schemas.watcher_schema import WatcherIntroduceSchema
from dispatch.app.dtos.watcher_dto import WatcherIntroduceResponse
from dispatch.app.ports.input.watcher_use_case import WatcherUseCase
from dispatch.dependencies.watcher_provider import get_watcher_use_case

watcher_router = APIRouter(prefix="/watcher", tags=["dispatch-watcher"])


@watcher_router.get("/myself")
async def introduce_myself(
    use_case: WatcherUseCase = Depends(get_watcher_use_case),
) -> WatcherIntroduceResponse:
    return await use_case.introduce_myself(WatcherIntroduceSchema(id=5, name="왓슨 트리아지"))
