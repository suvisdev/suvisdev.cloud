from __future__ import annotations

from abc import ABC, abstractmethod

from deolmi.app.dtos.score_dto import IssuedScoreDto, ScoreCommand, ScoreResultDto, VerifyCommand


class ScoreUseCase(ABC):
    @abstractmethod
    async def score(self, command: ScoreCommand) -> IssuedScoreDto:
        """SDK 신호로 점수를 매기고 서명 토큰을 발급한다."""

    @abstractmethod
    async def verify(self, command: VerifyCommand) -> ScoreResultDto:
        """고객 서버가 비밀 키로 토큰을 확인한다. 토큰은 한 번만 쓸 수 있다."""
