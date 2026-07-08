"""`admins` 테이블 관리자 1명 시드.

Usage (suvisdev 폴더에서):
  python scripts/seed_admin_user.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps"))


async def main() -> None:
    from core.matrix.grid_oracle_database_manager import create_tables, dispose_engine, reload_env
    from viewer.adapter.outbound.orm.admin_orm import seed_admin_if_empty

    reload_env()
    await create_tables()
    await seed_admin_if_empty()
    await dispose_engine()
    print("done - admin seeded (groups + admins tables).")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
