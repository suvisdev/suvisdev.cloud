"""Neon PostgreSQL — Mova·Viewer·Titanic ORM 연결 (SQLAlchemy 2.0 최신 비동기)."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ENV = _BACKEND_ROOT / ".env"

# 타입 명시 강화
_mova_engine: AsyncEngine | None = None
_viewer_engine: AsyncEngine | None = None
_mova_session_factory: async_sessionmaker[AsyncSession] | None = None
_viewer_session_factory: async_sessionmaker[AsyncSession] | None = None

_mova_init_error: str | None = None
_viewer_init_error: str | None = None
_active_mova_url: str | None = None
_active_viewer_url: str | None = None


def reload_env() -> None:
    load_dotenv(_BACKEND_ENV, override=True)


class MovaBase(DeclarativeBase):
    """Mova ORM (movies, rankings, …)."""

    pass


class ViewerBase(DeclarativeBase):
    """Viewer ORM (groups, admins, users)."""

    pass


class TitanicBase(DeclarativeBase):
    """Titanic James CSV 업로드 ORM."""

    pass


# Mova 모델 호환용
Base = MovaBase


def _normalize_database_url(url: str) -> str:
    normalized = url.strip()
    if normalized.startswith("postgresql://") and "+psycopg" not in normalized:
        normalized = normalized.replace("postgresql://", "postgresql+psycopg://", 1)

    # Neon/PostgreSQL 특유의 쿼리 파라미터 정리
    for param in [
        "channel_binding=require",
        "channel_binding=require&",
        "?channel_binding=require",
    ]:
        normalized = normalized.replace(param, "")
    return normalized.rstrip("?")


def _init_engine(
    url: str,
    label: str,
) -> tuple[AsyncEngine | None, async_sessionmaker[AsyncSession] | None, str | None, str | None]:
    # "URL이 같으면 기존 엔진 유지"는 호출부(ensure_*_database)가 판정한다
    if not url:
        return None, None, f"{label} URL이 설정되지 않았습니다.", None

    try:
        parsed = urlparse(url.replace("postgresql+psycopg://", "postgresql://"))

        # SQLAlchemy 2.0 비동기 엔진
        new_engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300,
        )

        new_factory = async_sessionmaker(
            bind=new_engine,
            expire_on_commit=False,
            autoflush=False,
        )

        logger.info("%s DB 엔진 초기화 성공: host=%s", label, parsed.hostname)
        return new_engine, new_factory, None, url

    except Exception as e:
        logger.exception("%s DB 엔진 생성 실패", label)
        return None, None, str(e), None


def ensure_mova_database() -> tuple[bool, str | None]:
    global _mova_session_factory, _mova_engine, _mova_init_error, _active_mova_url
    url = _normalize_database_url(os.getenv("MOVA_DATABASE_URL") or os.getenv("DATABASE_URL") or "")

    if _mova_session_factory is not None and _active_mova_url == url:
        return True, None

    reload_env()
    engine, factory, err, active = _init_engine(url, "Mova")
    _mova_engine, _mova_session_factory, _mova_init_error, _active_mova_url = (
        engine,
        factory,
        err,
        active,
    )
    return factory is not None, err


def ensure_viewer_database() -> tuple[bool, str | None]:
    global _viewer_session_factory, _viewer_engine, _viewer_init_error, _active_viewer_url
    reload_env()
    explicit_url = (os.getenv("VIEWER_DATABASE_URL") or "").strip()
    if explicit_url:
        url = _normalize_database_url(explicit_url)
    else:
        url = _normalize_database_url(
            os.getenv("MOVA_DATABASE_URL") or os.getenv("DATABASE_URL") or "",
        )

    if _viewer_session_factory is not None and _active_viewer_url == url:
        return True, None

    engine, factory, err, active = _init_engine(url, "Viewer")
    _viewer_engine, _viewer_session_factory, _viewer_init_error, _active_viewer_url = (
        engine,
        factory,
        err,
        active,
    )
    return factory is not None, err


# --- Dependency Injections (FastAPI) ---


async def get_mova_db() -> AsyncGenerator[AsyncSession, None]:
    ok, err = ensure_mova_database()
    if not ok or _mova_session_factory is None:
        raise HTTPException(status_code=503, detail=err)

    async with _mova_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_viewer_db() -> AsyncGenerator[AsyncSession, None]:
    ok, err = ensure_viewer_database()
    if not ok or _viewer_session_factory is None:
        raise HTTPException(status_code=503, detail=err)

    async with _viewer_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# --- Legacy Compatibility ---


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_mova_db():
        yield session


def get_mova_engine() -> AsyncEngine | None:
    ensure_mova_database()
    return _mova_engine


def get_viewer_engine() -> AsyncEngine | None:
    ensure_viewer_database()
    return _viewer_engine


def get_engine() -> AsyncEngine | None:
    return get_mova_engine()


def get_mova_session_factory() -> async_sessionmaker[AsyncSession]:
    ok, err = ensure_mova_database()
    if not ok or _mova_session_factory is None:
        raise RuntimeError(err or "Mova database not initialized")
    return _mova_session_factory


def get_viewer_session_factory() -> async_sessionmaker[AsyncSession]:
    ok, err = ensure_viewer_database()
    if not ok or _viewer_session_factory is None:
        raise RuntimeError(err or "Viewer database not initialized")
    return _viewer_session_factory


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return get_mova_session_factory()


async def verify_connection() -> tuple[bool, str | None]:
    ok, err = ensure_mova_database()
    if not ok or _mova_session_factory is None:
        return False, err or "Mova database not initialized"
    try:
        async with _mova_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        return False, str(e)

    ok_viewer, err_viewer = ensure_viewer_database()
    if not ok_viewer or _viewer_session_factory is None:
        return False, err_viewer or "Viewer database not initialized"
    try:
        async with _viewer_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        return False, str(e)

    return True, None


# --- Schema Management (2.0 Style) ---


async def _drop_legacy_mova_users_table(conn: Any) -> None:
    # 2.0 스타일의 결과 집합 처리
    query = text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'users'"
    )
    result = await conn.execute(query)
    columns = {row.column_name for row in result.mappings()}  # mappings() 사용 권장

    if not columns or "user_group_id" in columns:
        return
    if "group_id" in columns or "role" in columns:
        return
    if "preferred_genres" in columns or "nickname" in columns:
        logger.warning("Legacy Mova users table detected. Dropping for Viewer integration.")
        await conn.execute(text('DROP TABLE IF EXISTS "users" CASCADE'))


async def create_tables() -> None:
    """SQLAlchemy 2.0 방식의 테이블 일괄 생성."""
    await ensure_titanic_tables()
    try:
        import dispatch.adapter.outbound.orm  # noqa: F401 — DispatchAdressOrm (grid_neo_theone_base)
    except ModuleNotFoundError:
        logger.warning("Dispatch ORM not found, skipping.")
    import mova.adapter.outbound.orm  # noqa: F401

    try:
        import viewer.adapter.outbound.orm.admin_orm  # noqa: F401
        import viewer.adapter.outbound.orm.group_orm  # noqa: F401
        import viewer.adapter.outbound.orm.user_orm  # noqa: F401

        viewer_engine = get_viewer_engine()
        if viewer_engine:
            async with viewer_engine.begin() as conn:
                await _drop_legacy_mova_users_table(conn)
    except ModuleNotFoundError:
        logger.warning("Viewer models not found.")

    # mova/viewer 테이블 생성은 Alembic이 전담한다 (MOVA_V2_MIGRATION_HANDOFF.md §D).
    # create_all()로 우회 생성하지 않는다 — `alembic upgrade head`로만 적용.


async def ensure_titanic_tables() -> None:
    """DB 연결 준비 상태만 확인한다. **테이블 생성은 alembic이 단독으로 맡는다.**

    예전엔 여기서 `grid_neo_theone_base.Base.metadata.create_all()`을 돌려
    titanic_passengers·titanic_bookings·dispatch_adress·vision_uploads·
    hub_knowledge를 만들었는데, alembic도 같은 테이블을 관리해 **이중 관리**가
    됐다 — 새 ORM 모델을 추가할 때마다 autogenerate가 "이미 있는 테이블"을 보고
    `DuplicateTable`/`stamp` 우회를 반복하게 만든 원인이다(WORK_LOG 2026-07-30).

    2026-08-10에 실측으로 정리했다: 빈 DB에 `alembic upgrade head`만 돌린 결과가
    **프로덕션과 정확히 같은 36개 테이블**(차집합 0)이었다. 즉 create_all은 완전히
    중복이었다. 스키마 변경은 이제 마이그레이션으로만 한다.
    """
    ok, err = ensure_mova_database()
    if not ok:
        raise RuntimeError(err or "Mova database not initialized")

    if get_mova_engine() is None:
        raise RuntimeError("Mova engine not initialized")


async def dispose_engine() -> None:
    global _mova_engine, _viewer_engine, _mova_session_factory, _viewer_session_factory
    if _mova_engine is not None:
        await _mova_engine.dispose()
    if _viewer_engine is not None:
        await _viewer_engine.dispose()
    _mova_engine = None
    _viewer_engine = None
    _mova_session_factory = None
    _viewer_session_factory = None
