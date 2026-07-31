from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.adapter.outbound.pg.visitor_activity_pg_repository import (
    VisitorActivityPgRepository,
)
from analytics.app.ports.input.get_visitor_summary_use_case import GetVisitorSummaryUseCase
from analytics.app.ports.input.record_visit_use_case import RecordVisitUseCase
from analytics.app.ports.output.visitor_activity_repository import VisitorActivityRepository
from analytics.app.use_cases.get_visitor_summary_interactor import GetVisitorSummaryInteractor
from analytics.app.use_cases.record_visit_interactor import RecordVisitInteractor
from core.matrix.grid_oracle_database_manager import get_db


def get_visitor_activity_repository(
    session: AsyncSession = Depends(get_db),
) -> VisitorActivityRepository:
    return VisitorActivityPgRepository(session=session)


def get_record_visit_use_case(
    repository: VisitorActivityRepository = Depends(get_visitor_activity_repository),
) -> RecordVisitUseCase:
    return RecordVisitInteractor(repository=repository)


def get_visitor_summary_use_case(
    repository: VisitorActivityRepository = Depends(get_visitor_activity_repository),
) -> GetVisitorSummaryUseCase:
    return GetVisitorSummaryInteractor(repository=repository)
