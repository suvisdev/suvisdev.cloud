"""미니게임 Input Port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.adapter.inbound.api.schemas.games_schema import ScoreSaveSchema
from mova.app.dtos.games_dto import ChosungQuestionDto, LeaderboardDto, MemoryDeckDto


class GamesUseCase(ABC):
    @abstractmethod
    async def next_chosung_question(self) -> ChosungQuestionDto:
        """다음 초성 문제. 반복 호출로 새 문제를 계속 뽑는다."""

    @abstractmethod
    async def memory_deck(self, stage: int) -> MemoryDeckDto:
        """카드 뒤집기 N단계 카드 세트."""

    @abstractmethod
    async def save_score(self, user_id: int, payload: ScoreSaveSchema) -> None:
        """스코어 저장(로그인 유저만)."""

    @abstractmethod
    async def leaderboard(
        self, *, game_type: str, stage: int | None, limit: int, me_user_id: int | None
    ) -> LeaderboardDto:
        """리더보드 조회."""
