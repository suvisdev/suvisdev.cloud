from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.sentiment_analysis_dto import SentimentResult


class SentimentAnalysisUseCase(ABC):
    """감정 분석 입력 포트 (ABC) — Echo."""

    @abstractmethod
    def analyze(self, text: str) -> SentimentResult:
        pass
