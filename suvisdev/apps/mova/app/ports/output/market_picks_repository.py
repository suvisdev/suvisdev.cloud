"""picks 출력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_picks_dto import PickFeedbackDto


class PicksRepositoryPort(ABC):
    @abstractmethod
    async def update_feedback(
        self, pick_id: int, user_id: int, feedback: str | None
    ) -> PickFeedbackDto:
        """like | dislike | null 피드백 업데이트 — **본인 pick만**.

        소유자가 아니거나 없는 pick이면 `updated=False`를 돌려준다(존재 여부를
        구분해 알려주지 않는다 — 남의 pick_id를 훑어 존재를 캐낼 수 있으므로).
        """
