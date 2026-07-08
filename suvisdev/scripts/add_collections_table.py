"""collections 테이블 생성 (movies.collection_id FK 전제 조건).

Usage (suvisdev 폴더에서):
  python scripts/add_collections_table.py
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

    from core.matrix.grid_oracle_database_manager import dispose_engine, get_mova_engine, reload_env

    reload_env()

    engine = get_mova_engine()
    if engine is None:
        print("Mova engine unavailable — skip.")
        return

    async with engine.begin() as conn:
        if await table_exists(conn, "collections"):
            print("collections already exists — skip.")
        else:
            print("CREATE TABLE collections")
            await conn.execute(
                text(
                    """
                    CREATE TABLE collections (
                        id SERIAL PRIMARY KEY,
                        slug VARCHAR(64) NOT NULL UNIQUE,
                        name VARCHAR(255) NOT NULL,
                        description TEXT NOT NULL DEFAULT ''
                    )
                    """
                )
            )
            await conn.execute(
                text("CREATE INDEX ix_collections_slug ON collections (slug)")
            )
            print("collections table created.")

    await dispose_engine()
    print("done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
