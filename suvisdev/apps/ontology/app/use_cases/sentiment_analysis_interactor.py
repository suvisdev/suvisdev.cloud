from __future__ import annotations

from ontology.app.dtos.sentiment_analysis_dto import SentimentResult
from ontology.app.ports.input.sentiment_analysis_use_case import SentimentAnalysisUseCase
from ontology.app.ports.output.sentiment_analysis_port import SentimentAnalysisPort


class SentimentAnalysisInteractor(SentimentAnalysisUseCase):
    """sentiment_analysis_router → 입력 포트 → 출력 포트(KLUE-RoBERTa/Qwen QLoRA) → 감정 분석."""

    def __init__(self, sentiment_port: SentimentAnalysisPort) -> None:
        self._sentiment_port = sentiment_port

    def analyze(self, text: str) -> SentimentResult:
        return self._sentiment_port.analyze(text)
