from pathlib import Path

from ontology.adapter.outbound.resource_adapters.echo_sentiment.echo_sentiment_adapter import (
    EchoSentimentAdapter,
)
from ontology.app.ports.input.sentiment_analysis_use_case import SentimentAnalysisUseCase
from ontology.app.ports.output.sentiment_analysis_port import SentimentAnalysisPort
from ontology.app.use_cases.sentiment_analysis_interactor import SentimentAnalysisInteractor

_ADAPTER_DIR = Path(__file__).resolve().parent.parent / "runs" / "echo_sentiment" / "adapter"


def get_sentiment_analysis_port() -> SentimentAnalysisPort:
    return EchoSentimentAdapter(adapter_dir=_ADAPTER_DIR)


def get_sentiment_analysis_use_case() -> SentimentAnalysisUseCase:
    return SentimentAnalysisInteractor(sentiment_port=get_sentiment_analysis_port())
