"""movies — age_rating(varchar) 컬럼 추가.

Usage (suvisdev 폴더에서):
  python scripts/add_movies_age_rating.py
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


async def main() -> None:
    from sqlalchemy import text

    from core.matrix.grid_oracle_database_manager import dispose_engine, get_mova_engine, reload_env

    reload_env()

    engine = get_mova_engine()
    if engine is None:
        print("Mova engine unavailable — skip.")
        return

    async with engine.begin() as conn:
        if not await column_exists(conn, "movies", "age_rating"):
            print("ALTER movies ADD age_rating")
            await conn.execute(
                text("ALTER TABLE movies ADD COLUMN age_rating VARCHAR(8) NULL")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_movies_age_rating ON movies (age_rating)")
            )
        else:
            print("age_rating already exists — skip.")

    await dispose_engine()
    print("done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
