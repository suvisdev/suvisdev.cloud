"""tags.character_id FK (characters.id) 추가, actor_id 제거.

cast 태그는 영화–인물 연결(characters)을 검색 키워드로 노출한다.
기존 actor_id 컬럼이 있으면 characters와 조인해 backfill 후 삭제한다.

Usage (suvisdev 폴더에서):
  python scripts/add_tags_character_id.py
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


async def constraint_exists(conn, name: str) -> bool:
    from sqlalchemy import text

    r = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_schema = 'public' AND constraint_name = :n"
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
        if not await column_exists(conn, "tags", "character_id"):
            print("ALTER tags ADD character_id")
            await conn.execute(
                text("ALTER TABLE tags ADD COLUMN character_id INTEGER NULL"),
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_tags_character_id "
                    "ON tags (character_id)"
                ),
            )
        else:
            print("tags.character_id already exists")

        if await column_exists(conn, "tags", "actor_id"):
            print("BACKFILL character_id from actor_id + movie_id")
            await conn.execute(
                text(
                    """
                    UPDATE tags t
                    SET character_id = c.id
                    FROM characters c
                    WHERE t.character_id IS NULL
                      AND t.actor_id IS NOT NULL
                      AND c.movie_id = t.movie_id
                      AND c.actor_id = t.actor_id
                    """
                ),
            )

        if not await constraint_exists(conn, "fk_tags_character_id_characters"):
            print("ADD fk_tags_character_id_characters")
            await conn.execute(
                text(
                    "ALTER TABLE tags ADD CONSTRAINT fk_tags_character_id_characters "
                    "FOREIGN KEY (character_id) REFERENCES characters (id) "
                    "ON DELETE CASCADE"
                ),
            )

        if not await constraint_exists(conn, "uq_tags_character_id"):
            print("ADD uq_tags_character_id")
            await conn.execute(
                text(
                    "ALTER TABLE tags ADD CONSTRAINT uq_tags_character_id "
                    "UNIQUE (character_id)"
                ),
            )

        for cname in (
            "fk_tags_actor_id_actors",
            "uq_tags_movie_actor",
        ):
            if await constraint_exists(conn, cname):
                print(f"DROP CONSTRAINT {cname}")
                await conn.execute(text(f"ALTER TABLE tags DROP CONSTRAINT {cname}"))

        if await column_exists(conn, "tags", "actor_id"):
            print("DROP COLUMN tags.actor_id")
            await conn.execute(text("ALTER TABLE tags DROP COLUMN actor_id"))

    await dispose_engine()
    print("done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
