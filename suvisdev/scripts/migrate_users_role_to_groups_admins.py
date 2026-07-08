"""`users.role` 제거 → `groups` + `admins` + `users.group_id` 3테이블 구조.

Usage (suvisdev 폴더에서):
  python scripts/migrate_users_role_to_groups_admins.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps"))


async def column_exists(conn, table: str, column: str) -> bool:
    from sqlalchemy import text

    result = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return result.scalar_one_or_none() is not None


async def table_exists(conn, table: str) -> bool:
    from sqlalchemy import text

    result = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t"
        ),
        {"t": table},
    )
    return result.scalar_one_or_none() is not None


async def main() -> None:
    from sqlalchemy import text

    from core.matrix.grid_oracle_database_manager import (
        create_tables,
        dispose_engine,
        get_viewer_engine,
        reload_env,
    )
    from viewer.adapter.outbound.orm.admin_orm import Admin, seed_admin_if_empty
    from viewer.adapter.outbound.orm.group_orm import seed_groups_if_empty
    from viewer.app.dtos.role import UserRole

    reload_env()
    await create_tables()

    engine = get_viewer_engine()
    if engine is None:
        raise RuntimeError("Viewer DB not initialized")

    async with engine.begin() as conn:
        if not await column_exists(conn, "users", "role"):
            print("skip - users.role absent (already groups/admins/users)")
            await seed_groups_if_empty()
            await seed_admin_if_empty()
            await dispose_engine()
            return

        await seed_groups_if_empty()
        admin_group_id = (
            await conn.execute(
                text("SELECT id FROM groups WHERE code = :code"),
                {"code": UserRole.ADMIN},
            )
        ).scalar_one()
        user_group_id = (
            await conn.execute(
                text("SELECT id FROM groups WHERE code = :code"),
                {"code": UserRole.USER},
            )
        ).scalar_one()

        if not await table_exists(conn, "admins"):
            await conn.run_sync(Admin.__table__.create)

        admin_rows = (
            await conn.execute(
                text(
                    "SELECT id, username, password_hash, nickname, email "
                    "FROM users WHERE role = :role"
                ),
                {"role": UserRole.ADMIN},
            )
        ).mappings().all()

        for row in admin_rows:
            await conn.execute(
                text(
                    "INSERT INTO admins (group_id, username, password_hash, nickname, email) "
                    "VALUES (:group_id, :username, :password_hash, :nickname, :email) "
                    "ON CONFLICT (username) DO NOTHING"
                ),
                {
                    "group_id": admin_group_id,
                    "username": row["username"],
                    "password_hash": row["password_hash"],
                    "nickname": row["nickname"],
                    "email": row["email"],
                },
            )
            await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": row["id"]})

        if not await column_exists(conn, "users", "group_id"):
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN group_id INTEGER REFERENCES groups(id)")
            )

        await conn.execute(
            text("UPDATE users SET group_id = :gid WHERE group_id IS NULL"),
            {"gid": user_group_id},
        )
        await conn.execute(text("ALTER TABLE users ALTER COLUMN group_id SET NOT NULL"))
        await conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS role"))

    await seed_admin_if_empty()
    await dispose_engine()
    print("done — groups + admins + users (group_id) migrated.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
