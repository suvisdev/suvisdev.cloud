"""앱 플랫폼 API — 최소 지원 버전 (2026-09-27).

강제 업데이트 수단이 없으면 API가 바뀔 때 구버전 앱이 깨진 채 남는다. 값은 환경변수로
바꾼다(재배포 없이 Secret만 갱신): `GILDLE_APP_MIN_VERSION`·`GILDLE_APP_LATEST_VERSION`·
`GILDLE_APP_STORE_URL`. 앱은 자기 버전이 min_version보다 낮으면 업데이트를 요구한다.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query

from gildle.adapter.inbound.api.schemas.push_token_schema import AppVersionSchema

app_router = APIRouter(prefix="/app", tags=["gildle-app"])

_PLATFORMS = {"android"}


@app_router.get("/version", response_model=AppVersionSchema)
def app_version(platform: str = Query("android")) -> AppVersionSchema:
    if platform not in _PLATFORMS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 플랫폼: {platform}")
    return AppVersionSchema(
        platform=platform,
        min_version=os.getenv("GILDLE_APP_MIN_VERSION", "1.0.0"),
        latest_version=os.getenv("GILDLE_APP_LATEST_VERSION", "1.0.0"),
        store_url=os.getenv("GILDLE_APP_STORE_URL") or None,
    )
