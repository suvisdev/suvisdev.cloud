"""미니게임 Interactor — 얇게 포트 위임 + 스테이지 범위 가드."""

from __future__ import annotations

from fastapi import HTTPException

from mova.adapter.inbound.api.schemas.games_schema import ScoreSaveSchema
from mova.app.dtos.games_dto import (
    ChosungQuestionDto,
    LeaderboardDto,
    MemoryDeckDto,
    ScoreSaveCommand,
)
from mova.app.ports.input.games_use_case import GamesUseCase
from mova.app.ports.output.games_repository import GamesRepositoryPort

_MIN_RATING = 3.0  # 2026-08-13: 2.5 → 3.0 상향. 마이너 외국영화(태국·인도 등) 배제 강화.
_STAGE_MIN = 1
_STAGE_MAX = 10


class GamesInteractor(GamesUseCase):
    def __init__(self, repository: GamesRepositoryPort) -> None:
        self._repository = repository

    async def next_chosung_question(
        self, category: str = "all", exclude_ids: list[int] | None = None
    ) -> ChosungQuestionDto:
        if category not in ("all", "kr", "foreign"):
            raise HTTPException(status_code=400, detail="알 수 없는 category입니다.")
        q = await self._repository.sample_chosung_question(
            _MIN_RATING, category=category, exclude_ids=exclude_ids
        )
        if q is None:
            raise HTTPException(status_code=503, detail="문제를 만들 영화가 부족합니다.")
        return q

    async def memory_deck(self, stage: int) -> MemoryDeckDto:
        if not _STAGE_MIN <= stage <= _STAGE_MAX:
            raise HTTPException(
                status_code=400,
                detail=f"단계는 {_STAGE_MIN}~{_STAGE_MAX} 범위여야 합니다.",
            )
        deck = await self._repository.sample_memory_deck(stage, _MIN_RATING)
        expected = 2 * stage
        if len(deck.pairs) < expected:
            raise HTTPException(status_code=503, detail="카드를 만들 영화가 부족합니다.")
        return deck

    async def save_score(self, user_id: int, payload: ScoreSaveSchema) -> None:
        if payload.game_type == "memory":
            if payload.stage is None or not _STAGE_MIN <= payload.stage <= _STAGE_MAX:
                raise HTTPException(status_code=400, detail="memory 게임은 stage가 필요합니다.")
        elif payload.game_type == "chosung":
            if payload.stage is not None:
                raise HTTPException(status_code=400, detail="chosung 게임엔 stage가 없습니다.")
        await self._repository.save_score(
            ScoreSaveCommand(
                user_id=user_id,
                game_type=payload.game_type,
                stage=payload.stage,
                score=payload.score,
                hints_used=payload.hints_used,
            )
        )

    async def leaderboard(
        self, *, game_type: str, stage: int | None, limit: int, me_user_id: int | None
    ) -> LeaderboardDto:
        if game_type not in ("chosung", "memory"):
            raise HTTPException(status_code=400, detail="알 수 없는 게임입니다.")
        # 2026-08-13: memory 리더보드는 stage 무시 → 통합. stage 파라미터가 와도
        # 그냥 넘김(하위 호환).
        return await self._repository.leaderboard(
            game_type=game_type, stage=stage, limit=limit, me_user_id=me_user_id
        )
