"""movies — platforms(jsonb) 컬럼 추가 + 기존 platform(varchar) 데이터 이행 + platform 컬럼 제거.

기존 platform 값: 'netflix' → [{"provider": "netflix", "url": null, "type": null}]

Usage (suvisdev 폴더에서):
  python scripts/add_movies_platforms.py
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
        has_platforms = await column_exists(conn, "movies", "platforms")
        has_platform = await column_exists(conn, "movies", "platform")

        if not has_platforms:
            print("ALTER movies ADD platforms")
            await conn.execute(
                text("ALTER TABLE movies ADD COLUMN platforms JSONB NOT NULL DEFAULT '[]'::jsonb")
            )

            if has_platform:
                print("Migrating platform → platforms")
                await conn.execute(
                    text(
                        """
                        UPDATE movies
                        SET platforms = CASE
                            WHEN platform IS NOT NULL AND platform != ''
                            THEN jsonb_build_array(jsonb_build_object('provider', platform, 'url', null, 'type', null))
                            ELSE '[]'::jsonb
                        END
                        """
                    )
                )
        else:
            print("platforms already exists — skip add.")

        if has_platform:
            print("DROP COLUMN platform")
            await conn.execute(text("ALTER TABLE movies DROP COLUMN platform"))
        else:
            print("platform column not found — skip drop.")

    await dispose_engine()
    print("done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
