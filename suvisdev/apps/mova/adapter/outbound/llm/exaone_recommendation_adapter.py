"""EXAONE-3.5-7.8B-Instruct-AWQ(직접 서빙) 추천 어댑터 — RecommendationPort 구현체.

GeminiRecommendationAdapter와 동일한 프롬프트·파싱 로직(ChatPromptBuilder·
ChatReplyService)을 재사용하고, 실제 생성 호출만 core/lol의 AWQ 오케스트레이터로 교체한다.
tag_catalog는 더 이상 키워드 검색이 아니라 ontology Hub의 RAG 시맨틱 검색 결과를 받는다
(market_chat_interactor.py에서 조립).
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from core.lol.awq_exaone_orchestrator import AwqExaoneOrchestrator, AwqOrchestratorError
from mova.adapter.inbound.api.schemas.market_chat_schema import (
    MovaChatRecommendationSchema,
)
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.adapter.outbound.llm.chat_prompt import ChatPromptBuilder
from mova.adapter.outbound.llm.chat_reply import ChatReplyService
from mova.adapter.outbound.llm.intent_extraction import IntentExtractionService
from mova.app.ports.output.llm_errors import LLMError
from mova.app.ports.output.llm_output_port import RecommendationPort


class ExaoneRecommendationAdapter(RecommendationPort):
    def __init__(self) -> None:
        self._intent_svc = IntentExtractionService()
        self._prompt_builder = ChatPromptBuilder()
        self._reply_svc = ChatReplyService()
        self._orchestrator = AwqExaoneOrchestrator()

    def extract_intent(
        self, message: str, history: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        return self._intent_svc.extract(message, history=history)

    async def generate_recommendation(
        self,
        *,
        history: list[dict[str, str]],
        message: str,
        intent: dict[str, Any],
        tag_catalog: list[MovaSearchItemSchema],
        past_intents: list[Any],
        user_nickname: str | None,
        preferred_genres: list[str],
        model: Literal["flash", "flash15", "pro"] | None,
    ) -> tuple[str, list[MovaChatRecommendationSchema]]:
        prompt = self._prompt_builder.build_prompt(
            history,
            message,
            refined_query=intent["refined_query"],
            keywords=intent["keywords"],
            intent_type=intent["intent_type"],
            search_filters=intent["search_filters"],
            past_intents=past_intents,
            tag_catalog=tag_catalog,
            user_nickname=user_nickname,
            preferred_genres=preferred_genres,
        )
        try:
            raw = await asyncio.to_thread(self._orchestrator.generate, prompt)
        except AwqOrchestratorError as e:
            raise LLMError(e.detail, status_code=e.status_code) from e
        reply, recs = self._reply_svc.parse_gemini_reply(raw)
        recs = await self._reply_svc.enrich_from_db(recs, tag_catalog=tag_catalog)
        return reply, recs
