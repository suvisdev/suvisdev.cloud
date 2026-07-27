from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_session_factory
from silicon_valley.adapter.outbound.orm.pdf_summary_orm import PdfSummaryOrm
from silicon_valley.app.dtos.pdf_summary_dto import PdfSummaryRecord, PdfSummaryResponse
from silicon_valley.app.ports.output.pdf_summary_repository_port import PdfSummaryPort


class PdfSummaryRepository(PdfSummaryPort):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def save(self, record: PdfSummaryRecord) -> PdfSummaryResponse:
        if self._session is not None:
            return await self._persist(self._session, record)

        factory = get_mova_session_factory()
        async with factory() as session:
            response = await self._persist(session, record)
            await session.commit()
            return response

    async def _persist(
        self,
        session: AsyncSession,
        record: PdfSummaryRecord,
    ) -> PdfSummaryResponse:
        row = PdfSummaryOrm(
            filename=record.filename,
            extracted_text=record.extracted_text,
            summary=record.summary,
        )
        session.add(row)
        await session.flush()

        if self._session is not None:
            await session.commit()

        return PdfSummaryResponse(
            id=row.id,
            filename=record.filename,
            text_excerpt=record.extracted_text[:500],
            summary=record.summary,
        )
