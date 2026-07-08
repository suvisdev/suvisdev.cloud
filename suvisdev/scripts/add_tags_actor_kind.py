"""tags.actor_id, tags.tag_kind 컬럼 및 FK (actors.id) 추가.

Usage (suvisdev 폴더에서):
  python scripts/add_tags_actor_kind.py
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
        if not await column_exists(conn, "tags", "actor_id"):
            print("ALTER tags ADD actor_id")
            await conn.execute(text("ALTER TABLE tags ADD COLUMN actor_id INTEGER NULL"))
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_tags_actor_id ON tags (actor_id)"),
            )
        else:
            print("tags.actor_id already exists")

        if not await column_exists(conn, "tags", "tag_kind"):
            print("ALTER tags ADD tag_kind")
            await conn.execute(
                text(
                    "ALTER TABLE tags ADD COLUMN tag_kind VARCHAR(16) NOT NULL DEFAULT 'mood'"
                ),
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_tags_tag_kind ON tags (tag_kind)"),
            )
        else:
            print("tags.tag_kind already exists")

        if not await constraint_exists(conn, "fk_tags_actor_id_actors"):
            print("ADD fk_tags_actor_id_actors")
            await conn.execute(
                text(
                    "ALTER TABLE tags ADD CONSTRAINT fk_tags_actor_id_actors "
                    "FOREIGN KEY (actor_id) REFERENCES actors (id) ON DELETE CASCADE"
                ),
            )
        else:
            print("fk_tags_actor_id_actors already exists")

        if not await constraint_exists(conn, "uq_tags_movie_actor"):
            print("ADD uq_tags_movie_actor")
            await conn.execute(
                text(
                    "ALTER TABLE tags ADD CONSTRAINT uq_tags_movie_actor "
                    "UNIQUE (movie_id, actor_id)"
                ),
            )
        else:
            print("uq_tags_movie_actor already exists")

    await dispose_engine()
    print("done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
