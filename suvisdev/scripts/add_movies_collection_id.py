"""movies — collection_id(int, FK → collections.id) 컬럼 추가.

전제: add_collections_table.py 먼저 실행해야 합니다.

Usage (suvisdev 폴더에서):
  python scripts/add_collections_table.py   # 먼저
  python scripts/add_movies_collection_id.py
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
    from sqlalchemy import text

    from core.matrix.grid_oracle_database_manager import dispose_engine, get_mova_engine, reload_env

    reload_env()

    engine = get_mova_engine()
    if engine is None:
        print("Mova engine unavailable — skip.")
        return

    async with engine.begin() as conn:
        if not await column_exists(conn, "movies", "collection_id"):
            print("ALTER movies ADD collection_id")
            await conn.execute(
                text("ALTER TABLE movies ADD COLUMN collection_id INTEGER NULL")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_movies_collection_id ON movies (collection_id)")
            )

        if not await constraint_exists(conn, "fk_movies_collection_id"):
            print("ADD FK fk_movies_collection_id")
            await conn.execute(
                text(
                    "ALTER TABLE movies ADD CONSTRAINT fk_movies_collection_id "
                    "FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE SET NULL"
                )
            )
        else:
            print("fk_movies_collection_id already exists — skip.")

    await dispose_engine()
    print("done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
