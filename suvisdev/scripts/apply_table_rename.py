"""Neon에서 mova_* 테이블 rename + Viewer users 제거 (1회 실행, 재실행 안전).

Usage (suvisdev 폴더에서):
  python scripts/apply_table_rename.py
"""

from __future__ import annotations

import asyncio
import selectors
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "apps"
sys.path.insert(0, str(APPS))

RENAME_PAIRS: tuple[tuple[str, str], ...] = (
    ("mova_movies", "movies"),
    ("mova_actors", "actors"),
    ("mova_movie_characters", "characters"),
    ("mova_tags", "tags"),
    ("mova_movie_tags", "tags"),
    ("mova_rankings", "rankings"),
    ("mova_chat_intents", "chat"),
    ("mova_interactions", "reviews"),
    ("mova_reviews", "reviews"),
    ("mova_users", "users"),
)

VIEWER_DROP = ("user_groups",)


async def table_exists(conn, name: str) -> bool:
    from sqlalchemy import text

    r = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :n"
        ),
        {"n": name},
    )
    return r.scalar() is not None


async def is_viewer_users_table(conn) -> bool:
    """Viewer 회원 테이블만 제거 (Mova `users` 와 구분)."""
    from sqlalchemy import text

    if not await table_exists(conn, "users"):
        return False
    r = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'users' "
            "AND column_name = 'user_group_id'"
        ),
    )
    return r.scalar() is not None


async def row_count(conn, name: str) -> int:
    from sqlalchemy import text

    r = await conn.execute(text(f'SELECT COUNT(*) FROM "{name}"'))
    return int(r.scalar_one())


async def main() -> None:
    from database import dispose_engine, get_engine, reload_env
    from sqlalchemy import text

    reload_env()
    engine = get_engine()
    async with engine.begin() as conn:
        for table in VIEWER_DROP:
            if await table_exists(conn, table):
                print(f"DROP viewer table: {table}")
                await conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
        if await is_viewer_users_table(conn):
            print("DROP viewer table: users (has user_group_id)")
            await conn.execute(text('DROP TABLE IF EXISTS "users" CASCADE'))

        for old, new in RENAME_PAIRS:
            old_ok = await table_exists(conn, old)
            new_ok = await table_exists(conn, new)
            if old_ok and not new_ok:
                print(f"RENAME {old} -> {new}")
                await conn.execute(text(f'ALTER TABLE "{old}" RENAME TO "{new}"'))
                continue
            if not old_ok and new_ok:
                print(f"SKIP (already renamed): {new}")
                continue
            if old_ok and new_ok:
                new_rows = await row_count(conn, new)
                old_rows = await row_count(conn, old)
                if new_rows == 0:
                    print(f"DROP empty duplicate {new}, then RENAME {old} -> {new}")
                    await conn.execute(text(f'DROP TABLE "{new}" CASCADE'))
                    await conn.execute(text(f'ALTER TABLE "{old}" RENAME TO "{new}"'))
                elif old_rows == 0:
                    print(f"DROP empty legacy {old} (data in {new})")
                    await conn.execute(text(f'DROP TABLE "{old}" CASCADE'))
                elif old_rows >= new_rows:
                    print(
                        f"DROP duplicate {new} ({new_rows} rows), "
                        f"keep {old} ({old_rows} rows) -> RENAME to {new}"
                    )
                    await conn.execute(text(f'DROP TABLE "{new}" CASCADE'))
                    await conn.execute(text(f'ALTER TABLE "{old}" RENAME TO "{new}"'))
                else:
                    print(
                        f"WARN: both {old} and {new} exist "
                        f"(old_rows={old_rows}, new_rows={new_rows}) - manual merge needed"
                    )
                continue
            print(f"SKIP (missing both?): {old} / {new}")

    await dispose_engine()
    print("완료.")


if __name__ == "__main__":
    asyncio.run(
        main(),
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
    )
