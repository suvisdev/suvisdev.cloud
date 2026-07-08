"""`reviews` → `interactions`(action_type=review) 병합 (재실행 안전).

Usage (suvisdev 폴더에서):
  python scripts/merge_reviews_into_interactions.py
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
        has_reviews = await table_exists(conn, "reviews")
        has_interactions = await table_exists(conn, "interactions")

        if not has_interactions:
            print("interactions 없음 — create_tables() 후 다시 실행하세요.")
            return

        has_rating = await column_exists(conn, "interactions", "rating")

        if not has_rating:
            print("ALTER interactions: rating, body")
            await conn.execute(
                text(
                    """
                    ALTER TABLE interactions
                      ADD COLUMN IF NOT EXISTS rating DOUBLE PRECISION,
                      ADD COLUMN IF NOT EXISTS body TEXT;
                    """
                ),
            )

        if has_reviews:
            print("INSERT reviews → interactions (action_type=review)")
            await conn.execute(
                text(
                    """
                    INSERT INTO interactions (user_id, movie_id, action_type, action_at, rating, body)
                    SELECT r.user_id, r.movie_id, 'review', r.created_at, r.rating, r.body
                    FROM reviews r
                    WHERE NOT EXISTS (
                      SELECT 1 FROM interactions i
                      WHERE i.user_id = r.user_id
                        AND i.movie_id = r.movie_id
                        AND i.action_type = 'review'
                    );
                    """
                ),
            )
            print("DROP table: reviews")
            await conn.execute(text('DROP TABLE IF EXISTS "reviews" CASCADE'))

        print("CREATE UNIQUE INDEX uq_interactions_review (partial)")
        await conn.execute(
            text(
                "DROP INDEX IF EXISTS uq_interactions_review_user_movie"
            ),
        )
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_interactions_review_user_movie
                ON interactions (user_id, movie_id)
                WHERE action_type = 'review';
                """
            ),
        )
        print("병합 완료.")

    dispose_engine()
    print("done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
