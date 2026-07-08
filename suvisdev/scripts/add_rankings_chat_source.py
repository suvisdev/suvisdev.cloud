"""rankings — chat_id, source, score 컬럼 및 UNIQUE (rank, ranked_at, source).

Usage (suvisdev 폴더에서):
  python scripts/add_rankings_chat_source.py
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

    from core.matrix.grid_oracle_database_manager import (
        create_tables,
        dispose_engine,
        get_mova_engine,
        reload_env,
    )

    reload_env()
    await create_tables()

    engine = get_mova_engine()
    if engine is None:
        print("Mova engine unavailable — skip.")
        return

    async with engine.begin() as conn:
        if not await column_exists(conn, "rankings", "chat_id"):
            print("ALTER rankings ADD chat_id")
            await conn.execute(text("ALTER TABLE rankings ADD COLUMN chat_id INTEGER NULL"))
            await conn.execute(
                text(
                    "ALTER TABLE rankings ADD CONSTRAINT fk_rankings_chat_id_chat "
                    "FOREIGN KEY (chat_id) REFERENCES chat (id) ON DELETE SET NULL"
                ),
            )
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_rankings_chat_id ON rankings (chat_id)"))

        if not await column_exists(conn, "rankings", "source"):
            print("ALTER rankings ADD source")
            await conn.execute(
                text(
                    "ALTER TABLE rankings ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'box_office'"
                ),
            )
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_rankings_source ON rankings (source)"))

        if not await column_exists(conn, "rankings", "score"):
            print("ALTER rankings ADD score")
            await conn.execute(text("ALTER TABLE rankings ADD COLUMN score INTEGER NULL"))

        if await constraint_exists(conn, "uq_rankings_rank_date"):
            print("DROP uq_rankings_rank_date")
            await conn.execute(
                text("ALTER TABLE rankings DROP CONSTRAINT uq_rankings_rank_date"),
            )

        if not await constraint_exists(conn, "uq_rankings_rank_date_source"):
            print("ADD uq_rankings_rank_date_source")
            await conn.execute(
                text(
                    "ALTER TABLE rankings ADD CONSTRAINT uq_rankings_rank_date_source "
                    "UNIQUE (rank, ranked_at, source)"
                ),
            )

    await dispose_engine()
    print("done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
