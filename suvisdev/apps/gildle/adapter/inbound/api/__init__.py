from fastapi import APIRouter

from gildle.adapter.inbound.api.v1.route_router import route_router

# 앱 라우터 집약 — main.py(Composition Root)에서 이 gildle_router만 include한다.
gildle_router = APIRouter(prefix="/gildle", tags=["gildle"])
gildle_router.include_router(route_router)
