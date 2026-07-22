import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ontology.app.dtos.sentiment_analysis_dto import SentimentResult
from ontology.app.ports.input.sentiment_analysis_use_case import SentimentAnalysisUseCase
from ontology.dependencies.echo_sentiment_provider import get_sentiment_analysis_use_case

sentiment_analysis_router = APIRouter(tags=["sentiment"])


class AnalyzeSentimentRequest(BaseModel):
    text: str


@sentiment_analysis_router.post("/sentiment/analyze")
async def analyze_sentiment(
    body: AnalyzeSentimentRequest,
    use_case: SentimentAnalysisUseCase = Depends(get_sentiment_analysis_use_case),
) -> SentimentResult:
    # 호출당 EXAONE 4bit 로드(H4 참고, 수십 초) — 이벤트 루프 블로킹 방지
    return await asyncio.to_thread(use_case.analyze, body.text)
