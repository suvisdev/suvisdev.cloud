from __future__ import annotations

from abc import ABC, abstractmethod

from news.app.dtos.news_dtos import SummaryTarget
from news.domain.ko_summary import KoSummary


class SummarizerUnavailableError(Exception):
    """요약 모델 서버가 꺼졌거나 응답이 너무 느림 — 그 주기는 멈추고 다음 주기에 다시 시도한다."""


class ArticleSummarizerPort(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    async def summarize(self, target: SummaryTarget) -> KoSummary | None:
        """한국어 제목·요약. 모델 출력이 형식에 안 맞으면 None, 서버 문제면 SummarizerUnavailableError."""
