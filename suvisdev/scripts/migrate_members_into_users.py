"""members → users 프로필 흡수, chat.member_id 제거.

groups/user_groups는 사용하지 않음 — 권한은 users.role. 이후:
  python scripts/drop_groups_tables.py

Usage (suvisdev 폴더에서):
  python scripts/migrate_members_into_users.py
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

    r = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return r.scalar() is not None


async def table_exists(conn, table: str) -> bool:
    from sqlalchemy import text

    r = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t"
        ),
        {"t": table},
    )
    return r.scalar() is not None


async def main() -> None:
    from sqlalchemy import text

    from core.matrix.grid_oracle_database_manager import (
        create_tables,
        dispose_engine,
        get_viewer_engine,
        reload_env,
    )

    reload_env()
    await create_tables()

    engine = get_viewer_engine()
    if engine is None:
        print("Viewer engine unavailable — skip.")
        return

    async with engine.begin() as conn:
        profile_cols = (
            ("gender", "VARCHAR(16) NOT NULL DEFAULT 'undisclosed'"),
            ("age_group", "VARCHAR(16) NOT NULL DEFAULT 'undisclosed'"),
            ("birth_year", "INTEGER NULL"),
            ("preferred_genres", "JSONB NOT NULL DEFAULT '[]'::jsonb"),
            ("bio", "VARCHAR(255) NOT NULL DEFAULT ''"),
            ("updated_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
        )
        for col, ddl in profile_cols:
            if not await column_exists(conn, "users", col):
                print(f"ALTER users ADD {col}")
                await conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {ddl}"))

        if await table_exists(conn, "members"):
            print("COPY members → users")
            await conn.execute(
                text(
                    """
                    UPDATE users u SET
                        gender = COALESCE(m.gender, 'undisclosed'),
                        age_group = COALESCE(m.age_group, 'undisclosed'),
                        birth_year = m.birth_year,
                        preferred_genres = COALESCE(m.preferred_genres, '[]'::jsonb),
                        bio = COALESCE(m.bio, ''),
                        updated_at = COALESCE(m.updated_at, NOW())
                    FROM members m
                    WHERE m.user_id = u.id
                    """
                ),
            )

        if await column_exists(conn, "chat", "member_id"):
            print("DROP chat.member_id")
            await conn.execute(
                text("ALTER TABLE chat DROP CONSTRAINT IF EXISTS fk_chat_member_id_members"),
            )
            await conn.execute(text("DROP INDEX IF EXISTS ix_chat_member_id"))
            await conn.execute(text("ALTER TABLE chat DROP COLUMN member_id"))

        if await table_exists(conn, "member_groups"):
            print("DROP member_groups")
            await conn.execute(text("DROP TABLE member_groups CASCADE"))

        if await table_exists(conn, "members"):
            print("DROP members")
            await conn.execute(text("DROP TABLE members CASCADE"))

    await dispose_engine()
    print("done. run drop_groups_tables.py if groups/user_groups still exist.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
