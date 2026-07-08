"""picks 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_picks_dto import PickFeedbackDto


class PicksUseCase(ABC):
    @abstractmethod
    async def update_feedback(self, pick_id: int, feedback: str | None) -> PickFeedbackDto:
        pass
