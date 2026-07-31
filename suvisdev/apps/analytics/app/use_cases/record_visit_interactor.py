from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from analytics.app.ports.input.record_visit_use_case import RecordVisitUseCase
from analytics.app.ports.output.visitor_activity_repository import VisitorActivityRepository

logger = logging.getLogger(__name__)

_KST = ZoneInfo("Asia/Seoul")


class RecordVisitInteractor(RecordVisitUseCase):
    def __init__(self, *, repository: VisitorActivityRepository) -> None:
        self._repository = repository

    async def record(self, visitor_id: str) -> None:
        try:
            uuid.UUID(visitor_id)
        except (ValueError, AttributeError, TypeError):
            # 조작되거나 형식이 틀린 값은 집계에서 조용히 제외한다(공개 엔드포인트라 서버가 죽으면 안 됨).
            logger.warning("[RecordVisitInteractor] 유효하지 않은 visitor_id 무시")
            return

        now = datetime.now(UTC)
        visit_date = now.astimezone(_KST).date()
        await self._repository.upsert_visit(visitor_id, visit_date, now)
