"""assistants·groups·admin 시드.

Usage (suvisdev 폴더에서):
  python scripts/add_members_and_assistants.py
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
    from mova.adapter.outbound.pg.assistants_pg_repository import seed_assistants_if_empty
    from viewer.adapter.outbound.orm.admin_orm import seed_admin_if_empty
    from viewer.adapter.outbound.orm.group_orm import seed_groups_if_empty

    reload_env()
    await create_tables()
    await seed_groups_if_empty()
    await seed_admin_if_empty()
    await seed_assistants_if_empty()
    await dispose_engine()
    print("done - groups + admin + assistants seeded.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
