from __future__ import annotations

from abc import ABC, abstractmethod

from deolmi.app.dtos.score_dto import (
    IssuedScoreDto,
    ScoreCommand,
    ScoreEventDto,
    ScoreResultDto,
    VerifyCommand,
)


class ScoreUseCase(ABC):
    @abstractmethod
    async def score(self, command: ScoreCommand) -> IssuedScoreDto:
        """SDK 신호로 점수를 매기고 서명 토큰을 발급한다. 로그는 쓰지 않는다(record_event)."""

    @abstractmethod
    async def record_event(self, event: ScoreEventDto) -> None:
        """채점 로그 한 줄 저장 — 응답을 보낸 뒤 호출한다. 실패해도 예외를 내지 않는다."""

    @abstractmethod
    async def verify(self, command: VerifyCommand) -> ScoreResultDto:
        """고객 서버가 비밀 키로 토큰을 확인한다. 토큰은 한 번만 쓸 수 있다."""
