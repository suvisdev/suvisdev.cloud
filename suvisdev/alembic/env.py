from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_APPS_ROOT = _BACKEND_ROOT / "apps"
for _path in (_BACKEND_ROOT, _APPS_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_BACKEND_ROOT / ".env")

# gildle ORM 등록 — 모듈 import 시 테이블이 GildleBase.metadata에 붙는다.
import gildle.adapter.outbound.orm.hazard_zone_orm  # noqa: F401,E402
import gildle.adapter.outbound.orm.route_edge_orm  # noqa: F401,E402
import gildle.adapter.outbound.orm.route_node_orm  # noqa: F401,E402
import gildle.adapter.outbound.orm.route_request_orm  # noqa: F401,E402
import gildle.adapter.outbound.orm.route_result_orm  # noqa: F401,E402
import gildle.adapter.outbound.orm.tree_segment_orm  # noqa: F401,E402
import titanic.adapter.outbound.orm.passenger_jack_trainer_orm  # noqa: F401,E402
import titanic.adapter.outbound.orm.passenger_rose_model_orm  # noqa: F401,E402
from core.matrix.grid_oracle_database_manager import (  # noqa: E402
    TitanicBase,
    _normalize_database_url,
)
from gildle.adapter.outbound.orm.base import GildleBase  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 앱별 Base가 분리돼 있어 autogenerate가 모든 테이블을 보도록 metadata 리스트로 넘긴다.
target_metadata = [TitanicBase.metadata, GildleBase.metadata]


def _database_url() -> str:
    raw = os.getenv("MOVA_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    return _normalize_database_url(raw)


def run_migrations_offline() -> None:
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
