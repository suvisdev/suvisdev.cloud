"""chat.user_id 컬럼 추가 (Secom users 논리 참조, nullable).

Usage (suvisdev 폴더에서):
  python scripts/add_chat_user_id.py
"""

from __future__ import annotations

import asyncio
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


async def main() -> None:
    from database import dispose_engine, get_engine, reload_env
    from sqlalchemy import text

    reload_env()
    engine = get_engine()
    async with engine.begin() as conn:
        if not await column_exists(conn, "chat", "user_id"):
            print("ALTER chat ADD user_id")
            await conn.execute(
                text("ALTER TABLE chat ADD COLUMN user_id INTEGER NULL"),
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_chat_user_id ON chat (user_id)"),
            )
        else:
            print("chat.user_id already exists")

    await dispose_engine()
    print("done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
