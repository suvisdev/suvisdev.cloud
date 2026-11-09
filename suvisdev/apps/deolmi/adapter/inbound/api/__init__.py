from fastapi import APIRouter

from deolmi.adapter.inbound.api.v1.score_router import score_router
from deolmi.adapter.inbound.api.v1.site_admin_router import site_admin_router

# 앱 라우터 집약 — main.py(Composition Root)에서 이 deolmi_router만 include한다(prefix /api).
deolmi_router = APIRouter(prefix="/deolmi")
deolmi_router.include_router(score_router)
deolmi_router.include_router(site_admin_router)
