"""mova·길들 점검 모드 — `site_maintenance` 읽기·쓰기 (운영 제어 4단계).

- 읽기는 요청마다 부르므로 파드 안에서 10초 캐시한다. 토글한 파드는 바로, 다른 파드는 10초 안에 따라온다.
- 테이블이 없거나(이행 전) DB 가 안 닿으면 "점검 아님" — 점검 기능 고장으로 서비스를 막지 않는다.
- 쓰기 실패는 그대로 올린다(관리자가 눌렀는데 안 바뀐 걸 알아야 한다).
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import text

from core.matrix.grid_oracle_database_manager import get_viewer_session_factory

logger = logging.getLogger(__name__)

SERVICES: tuple[str, ...] = ("mova", "gildle")
_TTL_SECONDS = 10.0
_cache: tuple[float, dict[str, bool]] | None = None


async def load_maintenance(*, fresh: bool = False) -> dict[str, bool]:
    global _cache
    now = time.monotonic()
    if not fresh and _cache is not None and now - _cache[0] < _TTL_SECONDS:
        return dict(_cache[1])
    state = {s: False for s in SERVICES}
    try:
        factory = get_viewer_session_factory()
        async with factory() as session:
            rows = await session.execute(text("SELECT service, enabled FROM site_maintenance"))
            for service, enabled in rows.all():
                if service in state:
                    state[service] = bool(enabled)
    except Exception as e:  # 이행 전·DB 장애 — 막지 않는다
        logger.warning("[maintenance] 상태를 읽지 못해 점검 아님으로 봅니다: %s", e)
    _cache = (now, state)
    return dict(state)


async def set_maintenance(service: str, enabled: bool, updated_by: str) -> dict[str, bool]:
    if service not in SERVICES:
        raise ValueError(f"unknown service: {service}")
    factory = get_viewer_session_factory()
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO site_maintenance (service, enabled, updated_by, updated_at) "
                "VALUES (:service, :enabled, :updated_by, now()) "
                "ON CONFLICT (service) DO UPDATE SET enabled = EXCLUDED.enabled, "
                "updated_by = EXCLUDED.updated_by, updated_at = now()"
            ),
            {"service": service, "enabled": enabled, "updated_by": updated_by},
        )
        await session.commit()
    return await load_maintenance(fresh=True)


def maintenance_service_for(path: str) -> str | None:
    """요청 경로가 어느 서비스 API 인지. 막지 않을 경로(메인 사이트 로그인이 쓰는 /mova/whoami)는 None."""
    if path == "/mova/whoami":
        return None
    for service, prefix in (("mova", "/mova"), ("gildle", "/api/gildle")):
        if path == prefix or path.startswith(prefix + "/"):
            return service
    return None
