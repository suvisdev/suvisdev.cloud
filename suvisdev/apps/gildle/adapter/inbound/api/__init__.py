from fastapi import APIRouter

from gildle.adapter.inbound.api.v1.app_router import app_router
from gildle.adapter.inbound.api.v1.push_token_router import push_token_router
from gildle.adapter.inbound.api.v1.route_router import route_router
from gildle.adapter.inbound.api.v1.walk_router import walk_router

# 앱 라우터 집약 — main.py(Composition Root)에서 이 gildle_router만 include한다.
gildle_router = APIRouter(prefix="/gildle", tags=["gildle"])
gildle_router.include_router(route_router)
gildle_router.include_router(walk_router)
gildle_router.include_router(push_token_router)
gildle_router.include_router(app_router)
