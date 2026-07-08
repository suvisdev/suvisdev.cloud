"""picks PgRepository — PicksRepositoryPort 구현체."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_picks_orm import MovaPick
from mova.app.dtos.market_picks_dto import PickFeedbackDto
from mova.app.ports.output.market_picks_repository import PicksRepositoryPort
from mova.domain.value_objects.market_picks_vo import Feedback

logger = logging.getLogger(__name__)


class PicksPgRepository(PicksRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def update_feedback(self, pick_id: int, feedback: str | None) -> PickFeedbackDto:
        # 피드백 유효성·정규화는 도메인 VO(Feedback)가 단일 출처
        feedback_vo = Feedback.from_str(feedback)
        normalized = feedback_vo.value if feedback_vo else None

        pick = (
            await self._session.execute(select(MovaPick).where(MovaPick.id == pick_id))
        ).scalar_one_or_none()

        if pick is None:
            logger.debug("[PicksPgRepository] pick_id=%d 없음", pick_id)
            return PickFeedbackDto(pick_id=pick_id, feedback=None, updated=False)

        pick.feedback = normalized
        await self._session.commit()
        logger.debug("[PicksPgRepository] feedback 업데이트 pick_id=%d → %s", pick_id, normalized)
        return PickFeedbackDto(pick_id=pick_id, feedback=normalized, updated=True)
