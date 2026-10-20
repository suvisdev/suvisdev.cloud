from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from deolmi.app.dtos.score_dto import ScoreResultDto
from deolmi.app.dtos.site_dto import EventSummaryDto


class EventRepositoryPort(ABC):
    """/score마다 한 줄씩 쌓는 행동 로그 — 모델 재학습의 원천 데이터."""

    @abstractmethod
    async def add(
        self, site_id: int, ip: str, signals: dict[str, float], result: ScoreResultDto
    ) -> None: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def recent(self, n: int) -> list[EventSummaryDto]: ...

    @abstractmethod
    async def signals_by_verdict(self, verdict: str, limit: int) -> list[dict[str, Any]]: ...
