"""chat / reviews / picks.user_id -> users.id FK (동일 DB 전제).

Usage (suvisdev 폴더에서):
  python scripts/add_mova_user_id_fk.py

전제: SECOM_DATABASE_URL 비움 또는 MOVA_DATABASE_URL 과 동일.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "apps"
sys.path.insert(0, str(APPS))

FK_SPECS = (
    ("chat", "fk_chat_user_id_users", "user_id", "SET NULL"),
    ("picks", "fk_picks_user_id_users", "user_id", "SET NULL"),
    ("reviews", "fk_reviews_user_id_users", "user_id", "CASCADE"),
)


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
    from database import (
        _resolve_mova_url,
        _resolve_secom_url,
        dispose_engine,
        get_engine,
        reload_env,
    )
    from sqlalchemy import text

    reload_env()
    mova_url = _resolve_mova_url()
    secom_url = _resolve_secom_url()
    if secom_url != mova_url:
        print(
            "WARN: SECOM_DATABASE_URL != MOVA URL — FK는 동일 DB에서만 적용하세요.",
            file=sys.stderr,
        )

    engine = get_engine()
    async with engine.begin() as conn:
        if not await table_exists(conn, "users"):
            raise RuntimeError("users 테이블이 없습니다. Secom create_tables 먼저 실행하세요.")

        print("정리: 존재하지 않는 user_id 참조")
        await conn.execute(
            text(
                "UPDATE chat SET user_id = NULL "
                "WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)"
            ),
        )
        await conn.execute(
            text(
                "UPDATE picks SET user_id = NULL "
                "WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)"
            ),
        )
        await conn.execute(
            text("DELETE FROM reviews WHERE user_id NOT IN (SELECT id FROM users)"),
        )

        for table, fk_name, column, on_delete in FK_SPECS:
            if await constraint_exists(conn, fk_name):
                print(f"skip {fk_name} (already exists)")
                continue
            print(f"ADD {fk_name} ON {table}({column})")
            await conn.execute(
                text(
                    f'ALTER TABLE "{table}" ADD CONSTRAINT "{fk_name}" '
                    f'FOREIGN KEY ("{column}") REFERENCES users (id) ON DELETE {on_delete}'
                ),
            )

    await dispose_engine()
    print("done.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
