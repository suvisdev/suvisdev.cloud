from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import ensure_titanic_tables, get_mova_session_factory
from ontology.adapter.outbound.orm.vision_upload_orm import VisionUploadOrm
from ontology.app.dtos.vision_dto import (
    VisionImageCommand,
    VisionIntroduceQuery,
    VisionIntroduceResponse,
    VisionPosterFlagOverrideDto,
    VisionUploadResponse,
)
from ontology.app.ports.output.vision_port import VisionPort

logger = logging.getLogger(__name__)


class VisionRepository(VisionPort):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def introduce_myself(self, query: VisionIntroduceQuery) -> VisionIntroduceResponse:
        logger.info("[VisionRepository] introduce_myself 진입 | request_data=%s", query)
        return VisionIntroduceResponse(
            id=query.id * 10000,
            name=query.name + "가 레포지토리에 다녀옴",
        )

    async def save_image(self, command: VisionImageCommand) -> VisionUploadResponse:
        logger.info(
            "[VisionRepository] save_image 진입 | filename=%s size=%d",
            command.filename,
            len(command.content),
        )
        await ensure_titanic_tables()

        if self._session is not None:
            return await self._persist(self._session, command)

        factory = get_mova_session_factory()
        async with factory() as session:
            response = await self._persist(session, command)
            await session.commit()
            return response

    async def _persist(
        self,
        session: AsyncSession,
        command: VisionImageCommand,
    ) -> VisionUploadResponse:
        row = VisionUploadOrm(
            filename=command.filename,
            content=command.content,
            size_bytes=len(command.content),
            poster_confidence=command.poster_confidence,
            sharpness_score=command.sharpness_score,
            is_poster_warning=command.is_poster_warning,
        )
        session.add(row)
        await session.flush()

        if self._session is not None:
            await session.commit()

        return VisionUploadResponse(
            filename=command.filename,
            size_bytes=len(command.content),
            saved_path=f"db:vision_uploads#{row.id}",
            upload_id=row.id,
        )

    async def update_poster_flag(
        self, upload_id: int, is_poster_warning: bool
    ) -> VisionPosterFlagOverrideDto:
        logger.info(
            "[VisionRepository] update_poster_flag 진입 | upload_id=%d is_poster_warning=%s",
            upload_id,
            is_poster_warning,
        )
        await ensure_titanic_tables()

        if self._session is not None:
            return await self._apply_poster_flag(self._session, upload_id, is_poster_warning)

        factory = get_mova_session_factory()
        async with factory() as session:
            dto = await self._apply_poster_flag(session, upload_id, is_poster_warning)
            await session.commit()
            return dto

    async def _apply_poster_flag(
        self,
        session: AsyncSession,
        upload_id: int,
        is_poster_warning: bool,
    ) -> VisionPosterFlagOverrideDto:
        row = (
            await session.execute(select(VisionUploadOrm).where(VisionUploadOrm.id == upload_id))
        ).scalar_one_or_none()

        if row is None:
            return VisionPosterFlagOverrideDto(
                upload_id=upload_id, is_poster_warning=is_poster_warning, updated=False
            )

        row.is_poster_warning = is_poster_warning
        await session.flush()

        if self._session is not None:
            await session.commit()

        return VisionPosterFlagOverrideDto(
            upload_id=upload_id, is_poster_warning=is_poster_warning, updated=True
        )
