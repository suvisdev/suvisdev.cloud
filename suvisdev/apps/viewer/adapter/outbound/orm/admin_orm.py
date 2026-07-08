"""@see suvisdev/_claude/ENTITY_RULE.md — 관리자 계정 (`admins`)."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, select
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import get_viewer_session_factory
from viewer.adapter.outbound.orm.base_orm import ViewerModel
from viewer.adapter.outbound.orm.group_orm import get_group_id_by_code, seed_groups_if_empty
from viewer.app.dtos.role import UserRole

logger = logging.getLogger(__name__)


class Admin(ViewerModel):
    """관리자 계정 — `groups.code=admin`."""

    __tablename__ = "admins"

    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def _hash_password(raw_password: str) -> str:
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()


async def seed_admin_if_empty() -> None:
    """`admins` 테이블이 비어 있으면 기본 관리자 1명을 생성한다."""
    await seed_groups_if_empty()
    admin_group_id = await get_group_id_by_code(UserRole.ADMIN)

    factory = get_viewer_session_factory()
    async with factory() as session:
        admin_exists = await session.execute(select(Admin.id).limit(1))
        if admin_exists.scalar_one_or_none() is not None:
            return

        username = (os.getenv("VIEWER_ADMIN_USERNAME") or "admin").strip()
        password = os.getenv("VIEWER_ADMIN_PASSWORD") or "admin1234"
        nickname = (os.getenv("VIEWER_ADMIN_NICKNAME") or "Mova Admin").strip()
        email = (os.getenv("VIEWER_ADMIN_EMAIL") or f"{username}@mova.local").strip()

        session.add(
            Admin(
                group_id=admin_group_id,
                username=username,
                password_hash=_hash_password(password),
                nickname=nickname,
                email=email,
            ),
        )
        await session.commit()
        logger.info("[AdminOrm] default admin created — username=%s", username)
