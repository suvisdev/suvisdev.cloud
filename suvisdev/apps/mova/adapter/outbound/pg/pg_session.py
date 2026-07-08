from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_session_factory

T = TypeVar("T")


@asynccontextmanager
async def use_pg_session(
    injected: AsyncSession | None,
) -> AsyncIterator[tuple[AsyncSession, bool]]:
    if injected is not None:
        yield injected, False
        return

    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session, True
        except Exception:
            await session.rollback()
            raise


async def run_pg(
    injected: AsyncSession | None,
    fn: Callable[[AsyncSession], Awaitable[T]],
    *,
    commit: bool = True,
) -> T:
    async with use_pg_session(injected) as (session, should_commit):
        result = await fn(session)
        if should_commit and commit:
            await session.commit()
        return result
