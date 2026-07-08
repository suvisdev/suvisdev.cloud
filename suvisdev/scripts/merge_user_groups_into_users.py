"""`user_groups` + `users.user_group_id` → `users.role` 단일 컬럼 (재실행 안전).

Usage (suvisdev 폴더에서):
  python scripts/merge_user_groups_into_users.py
"""

from __future__ import annotations

import asyncio
import selectors
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "apps"
sys.path.insert(0, str(APPS))


async def column_exists(conn, table: str, column: str) -> bool:
    from sqlalchemy import text

    r = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return r.scalar() is not None


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


async def main() -> None:
    from database import dispose_engine, get_secom_engine, reload_env
    from sqlalchemy import text

    reload_env()
    engine = get_secom_engine()

    async with engine.begin() as conn:
        if not await table_exists(conn, "users"):
            print("users 테이블 없음 — create_tables() 후 다시 실행하세요.")
            return

        has_role = await column_exists(conn, "users", "role")
        has_fk = await column_exists(conn, "users", "user_group_id")
        has_groups = await table_exists(conn, "user_groups")

        if has_role and not has_fk and not has_groups:
            print("이미 병합됨 (users.role 만 존재).")
            return

        if not has_role:
            await conn.execute(
                text(
                    'ALTER TABLE "users" ADD COLUMN IF NOT EXISTS role VARCHAR(16) NOT NULL DEFAULT \'user\''
                ),
            )
            print("users.role 컬럼 추가")

        if has_fk and has_groups:
            await conn.execute(
                text(
                    """
                    UPDATE "users" u
                    SET role = g.code
                    FROM "user_groups" g
                    WHERE u.user_group_id = g.id
                    """
                ),
            )
            print("user_groups.code → users.role 이전")

        if has_fk:
            await conn.execute(
                text('ALTER TABLE "users" DROP CONSTRAINT IF EXISTS users_user_group_id_fkey'),
            )
            await conn.execute(text('ALTER TABLE "users" DROP COLUMN IF EXISTS user_group_id'))
            print("users.user_group_id 제거")

        if has_groups:
            await conn.execute(text('DROP TABLE IF EXISTS "user_groups" CASCADE'))
            print("user_groups 테이블 제거")

        await conn.execute(
            text('CREATE INDEX IF NOT EXISTS ix_users_role ON "users" (role)'),
        )
        print("done: users.role (admin / user)")

    await dispose_engine()


if __name__ == "__main__":
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    else:
        asyncio.run(main())
