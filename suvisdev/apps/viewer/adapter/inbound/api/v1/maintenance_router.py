"""공개 — mova·길들 점검 상태. 웹 레이아웃이 점검 안내를 띄울지 정할 때 읽는다.

  GET /viewer/maintenance   {"mova": bool, "gildle": bool}

바꾸는 쪽은 관리자 전용 POST /viewer/admin/ops/maintenance/{service} (admin_ops_router).
"""

from __future__ import annotations

from fastapi import APIRouter

from viewer.adapter.outbound.pg.maintenance_pg_repository import load_maintenance

maintenance_router = APIRouter(tags=["viewer"])


@maintenance_router.get("/maintenance")
async def get_maintenance() -> dict[str, bool]:
    return await load_maintenance()
