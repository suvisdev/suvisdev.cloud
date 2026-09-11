import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from shared.security.require_admin import AdminPrincipal, require_admin

from ontology.app.dtos.sentiment_analysis_dto import SentimentResult
from ontology.app.ports.input.sentiment_analysis_use_case import SentimentAnalysisUseCase
from ontology.dependencies.echo_sentiment_provider import get_sentiment_analysis_use_case

sentiment_analysis_router = APIRouter(tags=["sentiment"])


class AnalyzeSentimentRequest(BaseModel):
    text: str = Field(max_length=10_000)


# 2026-09-11 리뷰 H4: 익명 호출 1건당 EXAONE-2.4B 4bit 로드(수십 초 GPU 점유)
# 가능하던 표면 — 프론트 호출처가 없어 admin 전용으로 잠근다.
@sentiment_analysis_router.post("/sentiment/analyze")
async def analyze_sentiment(
    body: AnalyzeSentimentRequest,
    use_case: SentimentAnalysisUseCase = Depends(get_sentiment_analysis_use_case),
    _: AdminPrincipal = Depends(require_admin),
) -> SentimentResult:
    # 호출당 EXAONE 4bit 로드(H4 참고, 수십 초) — 이벤트 루프 블로킹 방지
    return await asyncio.to_thread(use_case.analyze, body.text)
