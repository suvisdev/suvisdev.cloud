"""chat_intents -> chat 테이블 rename (재실행 안전).

Usage (suvisdev 폴더에서):
  python scripts/rename_chat_intents_to_chat.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "apps"
sys.path.insert(0, str(APPS))


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
    from database import dispose_engine, get_engine, reload_env
    from sqlalchemy import text

    reload_env()
    engine = get_engine()
    async with engine.begin() as conn:
        has_old = await table_exists(conn, "chat_intents")
        has_new = await table_exists(conn, "chat")

        if has_new and not has_old:
            print("already renamed: chat")
            return

        if has_old and not has_new:
            print("RENAME chat_intents -> chat")
            await conn.execute(text('ALTER TABLE "chat_intents" RENAME TO "chat"'))
            print("done.")
            return

        if has_old and has_new:
            print("WARN: both chat_intents and chat exist")
            return

        print("no chat_intents table — skip")

    await dispose_engine()
    print("finished.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
