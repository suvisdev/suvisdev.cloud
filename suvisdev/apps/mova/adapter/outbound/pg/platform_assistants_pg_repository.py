"""어시스턴트 PgRepository — AssistantsRepositoryPort 구현체."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.platform_assistants_orm import MovaAssistant
from mova.app.dtos.platform_assistants_dto import AssistantDto, AssistantListDto
from mova.app.ports.output.platform_assistants_repository import AssistantsRepositoryPort

logger = logging.getLogger(__name__)


class AssistantsPgRepository(AssistantsRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self) -> AssistantListDto:
        rows = (
            (
                await self._session.execute(
                    select(MovaAssistant)
                    .where(MovaAssistant.is_active.is_(True))
                    .order_by(MovaAssistant.display_name)
                )
            )
            .scalars()
            .all()
        )

        logger.debug("[AssistantsPgRepository] list_active count=%d", len(rows))
        return AssistantListDto(items=[AssistantDto.from_orm(r) for r in rows])

    async def get_by_slug(self, slug: str) -> AssistantDto | None:
        row = (
            await self._session.execute(select(MovaAssistant).where(MovaAssistant.slug == slug))
        ).scalar_one_or_none()

        if not row:
            return None
        logger.debug("[AssistantsPgRepository] get_by_slug=%s found=%s", slug, bool(row))
        return AssistantDto.from_orm(row)
