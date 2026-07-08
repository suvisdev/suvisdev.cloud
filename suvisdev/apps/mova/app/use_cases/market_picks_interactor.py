"""picks Interactor — PicksUseCase 구현체."""

from __future__ import annotations

from mova.app.dtos.market_picks_dto import PickFeedbackDto
from mova.app.ports.input.market_picks_use_case import PicksUseCase
from mova.app.ports.output.market_picks_repository import PicksRepositoryPort


class PicksInteractor(PicksUseCase):
    def __init__(self, repository: PicksRepositoryPort) -> None:
        self._repository = repository

    async def update_feedback(self, pick_id: int, feedback: str | None) -> PickFeedbackDto:
        return await self._repository.update_feedback(pick_id, feedback)
