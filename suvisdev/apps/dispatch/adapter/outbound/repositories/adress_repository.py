from __future__ import annotations

import logging

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from dispatch.adapter.outbound.orm.adress_orm import DispatchAdressOrm
from dispatch.app.dtos.adress_dto import (
    AdressCommand,
    AdressIntroduceQuery,
    AdressIntroduceResponse,
    AdressSearchQuery,
    AdressSearchResult,
)
from dispatch.app.ports.output.adress_port import AdressPort

logger = logging.getLogger(__name__)


class AdressRepository(AdressPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_save(self, commands: list[AdressCommand]) -> int:
        if not commands:
            return 0
        values = [
            {
                "first_name": cmd.first_name,
                "middle_name": cmd.middle_name,
                "last_name": cmd.last_name,
                "phonetic_first_name": cmd.phonetic_first_name,
                "phonetic_middle_name": cmd.phonetic_middle_name,
                "phonetic_last_name": cmd.phonetic_last_name,
                "name_prefix": cmd.name_prefix,
                "name_suffix": cmd.name_suffix,
                "nickname": cmd.nickname,
                "file_as": cmd.file_as,
                "organization_name": cmd.organization_name,
                "organization_title": cmd.organization_title,
                "organization_department": cmd.organization_department,
                "birthday": cmd.birthday,
                "notes": cmd.notes,
                "photo": cmd.photo,
                "labels": cmd.labels,
                "email_label": cmd.email_label,
                "email": cmd.email,
            }
            for cmd in commands
        ]
        stmt = (
            insert(DispatchAdressOrm)
            .values(values)
            .on_conflict_do_nothing(index_elements=["email"])
        )
        result = await self._session.execute(stmt)
        saved = result.rowcount
        await self._session.flush()
        logger.info("[AdressRepository] %d개 주소록 저장 (중복 제외)", saved)
        return saved

    async def introduce_myself(self, query: AdressIntroduceQuery) -> AdressIntroduceResponse:
        return AdressIntroduceResponse(id=query.id, name=query.name)

    async def search(self, query: AdressSearchQuery) -> list[AdressSearchResult]:
        pattern = f"%{query.q}%"
        stmt = (
            select(DispatchAdressOrm)
            .where(
                or_(
                    DispatchAdressOrm.first_name.ilike(pattern),
                    DispatchAdressOrm.last_name.ilike(pattern),
                    DispatchAdressOrm.nickname.ilike(pattern),
                    DispatchAdressOrm.email.ilike(pattern),
                )
            )
            .limit(10)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [
            AdressSearchResult(
                name=(f"{row.first_name} {row.last_name}".strip() or row.nickname or row.email),
                email=row.email,
            )
            for row in rows
        ]
