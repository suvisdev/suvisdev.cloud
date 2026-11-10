from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.sentiment_analysis_dto import SentimentResult


class SentimentAnalysisPort(ABC):
    """감정 분석 아웃바운드 포트 (ABC) — Echo."""

    @abstractmethod
    def analyze(self, text: str) -> SentimentResult:
        """텍스트의 감정 극성·신뢰도·(생성형)근거를 반환한다."""

    @abstractmethod
    def analyze_batch(self, texts: list[str]) -> list[SentimentResult | None]:
        """여러 텍스트를 한 번에 분석한다. 실패한 항목은 None."""
