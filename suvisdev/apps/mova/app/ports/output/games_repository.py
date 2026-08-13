"""미니게임 Output Port — 랜덤 영화 표본, 카드 덱, 스코어 저장·리더보드."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.games_dto import (
    ChosungQuestionDto,
    LeaderboardDto,
    MemoryDeckDto,
    ScoreSaveCommand,
)


class GamesRepositoryPort(ABC):
    @abstractmethod
    async def sample_chosung_question(
        self, min_rating: float, *, category: str = "all"
    ) -> ChosungQuestionDto | None:
        """rating >= min_rating인 영화 중 한 편을 무작위로 뽑아 초성 문제 구성.

        category: 'all' | 'kr' | 'foreign'. kr=original_language=='ko',
        foreign=그 외. 'all'은 필터 없음.
        """

    @abstractmethod
    async def sample_memory_deck(self, stage: int, min_rating: float) -> MemoryDeckDto:
        """N단계(1~10): 2N쌍(4N장) 만들 페어를 무작위로 뽑는다.

        각 쌍은 (포스터 카드, 제목 카드) 두 장으로 프론트가 펼친다.
        """

    @abstractmethod
    async def save_score(self, command: ScoreSaveCommand) -> None:
        """게임 결과 저장 — 로그인 유저만 호출."""

    @abstractmethod
    async def leaderboard(
        self, *, game_type: str, stage: int | None, limit: int, me_user_id: int | None
    ) -> LeaderboardDto:
        """게임별(카드 뒤집기는 단계별) TOP N + 내 최고 기록."""
