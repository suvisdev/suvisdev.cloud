"""movie_tags -> tags, movie_characters -> characters (재실행 안전).

Usage (suvisdev 폴더에서):
  python scripts/rename_movie_tags_and_characters.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "apps"
sys.path.insert(0, str(APPS))

RENAMES: tuple[tuple[str, str], ...] = (
    ("movie_tags", "tags"),
    ("movie_characters", "characters"),
)


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
        for old, new in RENAMES:
            has_old = await table_exists(conn, old)
            has_new = await table_exists(conn, new)
            if has_old and not has_new:
                print(f"RENAME {old} -> {new}")
                await conn.execute(text(f'ALTER TABLE "{old}" RENAME TO "{new}"'))
            elif has_new and not has_old:
                print(f"skip (already {new})")
            elif has_old and has_new:
                print(f"WARN: both {old} and {new} exist")
            else:
                print(f"skip (no {old})")

        if await table_exists(conn, "tags"):
            await conn.execute(
                text(
                    "ALTER TABLE tags "
                    "DROP CONSTRAINT IF EXISTS uq_movie_tags_movie_slug"
                ),
            )
            await conn.execute(
                text(
                    "ALTER TABLE tags "
                    "ADD CONSTRAINT uq_tags_movie_slug "
                    "UNIQUE (movie_id, slug)"
                ),
            )

        if await table_exists(conn, "characters"):
            await conn.execute(
                text(
                    "ALTER TABLE characters "
                    "DROP CONSTRAINT IF EXISTS uq_movie_characters_movie_actor"
                ),
            )
            await conn.execute(
                text(
                    "ALTER TABLE characters "
                    "ADD CONSTRAINT uq_characters_movie_actor "
                    "UNIQUE (movie_id, actor_id)"
                ),
            )

    await dispose_engine()
    print("done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
