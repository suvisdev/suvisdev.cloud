"""`interactions` 테이블을 `reviews`로 rename (재실행 안전).

Usage (suvisdev 폴더에서):
  python scripts/rename_interactions_to_reviews.py
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
        has_interactions = await table_exists(conn, "interactions")
        has_reviews = await table_exists(conn, "reviews")

        if has_reviews and not has_interactions:
            print("already renamed: reviews")
            return

        if has_interactions and not has_reviews:
            print("RENAME TABLE interactions TO reviews")
            await conn.execute(text('ALTER TABLE "interactions" RENAME TO "reviews"'))
            await conn.execute(
                text("DROP INDEX IF EXISTS uq_interactions_review_user_movie"),
            )
            await conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_reviews_rating_user_movie
                    ON reviews (user_id, movie_id)
                    WHERE action_type = 'review';
                    """
                ),
            )
            print("done.")
            return

        if has_interactions and has_reviews:
            print("both interactions and reviews exist — manual merge required")
            return

        print("no interactions table — skip")

    await dispose_engine()
    print("finished.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
