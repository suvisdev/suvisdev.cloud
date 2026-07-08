"""`tags` + `movie_tags`(tag_id) → `movie_tags`(slug, label) 단일 테이블로 병합 (재실행 안전).

Usage (suvisdev 폴더에서):
  python scripts/merge_tags_tables.py
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
        has_tags = await table_exists(conn, "tags")
        has_mt = await table_exists(conn, "movie_tags")
        if not has_mt:
            print("movie_tags 없음 — create_tables() 후 다시 실행하세요.")
            return

        has_tag_id = await column_exists(conn, "movie_tags", "tag_id")
        has_slug = await column_exists(conn, "movie_tags", "slug")

        if has_slug and not has_tag_id:
            print("이미 병합된 스키마입니다.")
            if has_tags:
                print("DROP legacy table: tags")
                await conn.execute(text('DROP TABLE IF EXISTS "tags" CASCADE'))
            return

        if has_tag_id and has_tags:
            print("merge: tags → movie_tags (slug, label, description)")
            await conn.execute(
                text(
                    """
                    ALTER TABLE movie_tags
                      ADD COLUMN IF NOT EXISTS slug VARCHAR(64),
                      ADD COLUMN IF NOT EXISTS label VARCHAR(255),
                      ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';
                    """
                ),
            )
            await conn.execute(
                text(
                    """
                    UPDATE movie_tags mt
                    SET slug = t.slug,
                        label = t.label,
                        description = COALESCE(t.description, '')
                    FROM tags t
                    WHERE mt.tag_id = t.id AND mt.slug IS NULL;
                    """
                ),
            )
            await conn.execute(
                text(
                    """
                    UPDATE movie_tags
                    SET slug = 'tag-' || id::text,
                        label = 'tag-' || id::text,
                        description = ''
                    WHERE slug IS NULL;
                    """
                ),
            )
            await conn.execute(
                text("ALTER TABLE movie_tags ALTER COLUMN slug SET NOT NULL"),
            )
            await conn.execute(
                text("ALTER TABLE movie_tags ALTER COLUMN label SET NOT NULL"),
            )
            await conn.execute(
                text(
                    "ALTER TABLE movie_tags DROP CONSTRAINT IF EXISTS uq_movie_tags_movie_tag"
                ),
            )
            await conn.execute(
                text(
                    "ALTER TABLE movie_tags DROP CONSTRAINT IF EXISTS movie_tags_tag_id_fkey"
                ),
            )
            await conn.execute(text("ALTER TABLE movie_tags DROP COLUMN IF EXISTS tag_id"))
            await conn.execute(
                text(
                    "ALTER TABLE movie_tags "
                    "ADD CONSTRAINT uq_movie_tags_movie_slug "
                    "UNIQUE (movie_id, slug)"
                ),
            )
            print("DROP table: tags")
            await conn.execute(text('DROP TABLE IF EXISTS "tags" CASCADE'))
            print("병합 완료.")
            return

        if has_tag_id and not has_tags:
            print("tags 테이블 없음 — movie_tags tag_id 컬럼만 제거 시도")
            await conn.execute(text("ALTER TABLE movie_tags DROP COLUMN IF EXISTS tag_id"))
            return

        print("변경 없음 (신규 DB는 create_tables()로 생성).")

    dispose_engine()
    print("done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
