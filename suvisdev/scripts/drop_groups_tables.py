"""groups·user_groups 테이블 제거 — 권한은 users.role(admin/user)만 사용.

Usage (suvisdev 폴더에서):
  python scripts/drop_groups_tables.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps"))


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
        if await table_exists(conn, "user_groups"):
            print("DROP user_groups")
            await conn.execute(text("DROP TABLE user_groups CASCADE"))

        if await table_exists(conn, "groups"):
            print("DROP groups")
            await conn.execute(text("DROP TABLE groups CASCADE"))

    await dispose_engine()
    print("done — groups/user_groups dropped; use users.role (admin|user).")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
