"""DB 연결·테이블 생성 검증 (viewer → mova 순서, FK 포함)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for p in (_BACKEND, _APPS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from sqlalchemy import text

from core.matrix.grid_oracle_database_manager import (
    create_tables,
    dispose_engine,
    get_mova_engine,
    get_viewer_engine,
    reload_env,
    verify_connection,
)
from viewer.adapter.outbound.orm.user_orm import seed_viewer_if_empty

VIEWER_TABLES = ("groups", "admins", "users")
MOVA_TABLES = (
    "movies",
    "actors",
    "characters",
    "tags",
    "rankings",
    "chat",
    "picks",
    "reviews",
    "assistants",
)
TITANIC_TABLES = ("titanic_persons", "titanic_bookings")


async def _list_public_tables(engine) -> list[str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
        )
        return [row[0] for row in result.all()]


async def _check_fk(engine, table: str, column: str, ref_table: str) -> bool:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "  ON tc.constraint_name = kcu.constraint_name "
                "  AND tc.table_schema = kcu.table_schema "
                "JOIN information_schema.constraint_column_usage ccu "
                "  ON ccu.constraint_name = tc.constraint_name "
                "  AND ccu.table_schema = tc.table_schema "
                "WHERE tc.constraint_type = 'FOREIGN KEY' "
                "  AND tc.table_schema = 'public' "
                "  AND tc.table_name = :table "
                "  AND kcu.column_name = :column "
                "  AND ccu.table_name = :ref_table"
            ),
            {"table": table, "column": column, "ref_table": ref_table},
        )
        return result.scalar_one_or_none() is not None


async def main() -> None:
    reload_env()
    print("=== 1. DB 연결 확인 ===")
    ok, err = await verify_connection()
    if not ok:
        print(f"FAIL: {err}")
        await dispose_engine()
        sys.exit(1)
    print("OK: Mova + Viewer SELECT 1 성공")

    print("\n=== 2. create_tables() 실행 ===")
    await create_tables()
    print("OK: create_tables 완료")

    print("\n=== 3. seed_viewer_if_empty() 실행 ===")
    await seed_viewer_if_empty()
    print("OK: viewer seed 완료")

    mova_engine = get_mova_engine()
    viewer_engine = get_viewer_engine()
    if mova_engine is None or viewer_engine is None:
        print("FAIL: engine 초기화 실패")
        await dispose_engine()
        sys.exit(1)

    mova_tables = await _list_public_tables(mova_engine)
    viewer_tables = await _list_public_tables(viewer_engine)
    same_db = mova_tables == viewer_tables

    print(f"\n=== 4. public 테이블 목록 ({len(mova_tables)}개) ===")
    for name in mova_tables:
        print(f"  - {name}")
    if not same_db:
        print(f"\n(Viewer 별도 DB — {len(viewer_tables)}개)")

    print("\n=== 5. 필수 테이블 존재 여부 ===")
    all_ok = True
    for label, expected in (
        ("Viewer", VIEWER_TABLES),
        ("Mova", MOVA_TABLES),
        ("Titanic", TITANIC_TABLES),
    ):
        missing = [t for t in expected if t not in mova_tables]
        if missing:
            all_ok = False
            print(f"  FAIL [{label}] 누락: {missing}")
        else:
            print(f"  OK   [{label}] {len(expected)}개 모두 존재")

    print("\n=== 6. cross-metadata FK (chat/picks/reviews → users) ===")
    for table, column in (("chat", "user_id"), ("picks", "user_id"), ("reviews", "user_id")):
        if table not in mova_tables:
            print(f"  SKIP {table}.{column} (테이블 없음)")
            continue
        has_fk = await _check_fk(mova_engine, table, column, "users")
        status = "OK" if has_fk else "FAIL"
        if not has_fk:
            all_ok = False
        print(f"  {status}  {table}.{column} → users.id")

    print("\n=== 7. Viewer seed 데이터 ===")
    async with viewer_engine.connect() as conn:
        for table in ("groups", "admins", "users"):
            count = (await conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))).scalar_one()
            print(f"  {table}: {count} rows")

    await dispose_engine()
    print("\n=== 결과 ===")
    if all_ok:
        print("전체 PASS")
    else:
        print("일부 FAIL — 위 로그 확인")
        sys.exit(1)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
