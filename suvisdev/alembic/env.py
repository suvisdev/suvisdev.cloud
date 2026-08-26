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

# contents ORM 등록 — 모듈 import 시 테이블이 ContentsBase.metadata에 붙는다.
from pgvector.sqlalchemy import Vector  # noqa: F401,E402

import contents.adapter.outbound.orm.player_orm  # noqa: F401,E402
import contents.adapter.outbound.orm.schedule_orm  # noqa: F401,E402
import contents.adapter.outbound.orm.stadium_orm  # noqa: F401,E402
import contents.adapter.outbound.orm.team_orm  # noqa: F401,E402

# grid_neo_theone_base.Base 등록 — titanic_passengers/bookings, dispatch_adress/inbox,
# vision_uploads, pdf_loader_documents가 실제로 붙는 Base (TitanicBase와는 별개,
# 지금까지 target_metadata 밖이었음).
import dispatch.adapter.outbound.orm.adress_orm  # noqa: F401,E402
import dispatch.adapter.outbound.orm.receive_orm  # noqa: F401,E402
import execsuite.adapter.outbound.orm.pdf_loader_orm  # noqa: F401,E402

# gildle ORM 등록 — 모듈 import 시 테이블이 GildleBase.metadata에 붙는다.
import gildle.adapter.outbound.orm.hazard_zone_orm  # noqa: F401,E402
import gildle.adapter.outbound.orm.route_edge_orm  # noqa: F401,E402
import gildle.adapter.outbound.orm.route_node_orm  # noqa: F401,E402
import gildle.adapter.outbound.orm.route_request_orm  # noqa: F401,E402
import gildle.adapter.outbound.orm.route_result_orm  # noqa: F401,E402
import gildle.adapter.outbound.orm.tree_segment_orm  # noqa: F401,E402

# mova ORM 등록 — 패키지 __init__이 전체 서브모듈을 import해 MovaBase.metadata에 붙인다.
import mova.adapter.outbound.orm  # noqa: F401,E402
import ontology.adapter.outbound.orm.vision_upload_orm  # noqa: F401,E402
import titanic.adapter.outbound.orm.passenger_jack_trainer_orm  # noqa: F401,E402
import titanic.adapter.outbound.orm.passenger_rose_model_orm  # noqa: F401,E402

# viewer ORM 등록 — 모듈 import 시 테이블이 ViewerBase.metadata에 붙는다.
import viewer.adapter.outbound.orm.admin_orm  # noqa: F401,E402
import viewer.adapter.outbound.orm.group_orm  # noqa: F401,E402
import viewer.adapter.outbound.orm.user_identity_orm  # noqa: F401,E402
import viewer.adapter.outbound.orm.user_orm  # noqa: F401,E402
from contents.adapter.outbound.orm.base import ContentsBase  # noqa: E402
from core.matrix.grid_neo_theone_base import Base as NeoTheOneBase  # noqa: E402
from core.matrix.grid_oracle_database_manager import (  # noqa: E402
    MovaBase,
    TitanicBase,
    ViewerBase,
    _normalize_database_url,
)
from gildle.adapter.outbound.orm.base import GildleBase  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 앱별 Base가 분리돼 있어 autogenerate가 모든 테이블을 보도록 metadata 리스트로 넘긴다.
target_metadata = [
    TitanicBase.metadata,
    NeoTheOneBase.metadata,
    GildleBase.metadata,
    ContentsBase.metadata,
    MovaBase.metadata,
    ViewerBase.metadata,
]


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
