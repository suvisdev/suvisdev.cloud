"""@see suvisdev/_claude/ENTITY_RULE.md — 권한 그룹 (`groups`)."""

from __future__ import annotations

import logging

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import get_viewer_session_factory
from viewer.adapter.outbound.orm.base_orm import ViewerModel
from viewer.app.dtos.role import UserRole

logger = logging.getLogger(__name__)

_DEFAULT_GROUPS: tuple[tuple[str, str, str], ...] = (
    (UserRole.ADMIN, "관리자", "Mova 관리자 그룹"),
    (UserRole.USER, "일반 사용자", "Mova 일반 사용자 그룹"),
)


class Group(ViewerModel):
    """권한 그룹 — `admin` / `user` 코드."""

    __tablename__ = "groups"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")


async def seed_groups_if_empty() -> None:
    factory = get_viewer_session_factory()
    async with factory() as session:
        added = False
        for code, name, description in _DEFAULT_GROUPS:
            exists = await session.execute(select(Group.id).where(Group.code == code))
            if exists.scalar_one_or_none() is None:
                session.add(Group(code=code, name=name, description=description))
                added = True
        if added:
            await session.commit()
            logger.info("[GroupOrm] default groups seeded — admin, user")


async def get_group_id_by_code(code: str) -> int:
    await seed_groups_if_empty()
    factory = get_viewer_session_factory()
    async with factory() as session:
        row = (
            await session.execute(select(Group.id).where(Group.code == code))
        ).scalar_one_or_none()
        if row is None:
            raise ValueError(f"그룹 코드 '{code}'를 찾을 수 없습니다.")
        return row
