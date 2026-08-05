"""mova 채팅 전용 파인튜닝 LoRA 어댑터(lora_server) — RecommendationPort 구현체.

OllamaExaoneRecommendationAdapter/QwenRecommendationAdapter와 완전히 동일한
프롬프트·파싱 로직(ChatPromptBuilder·ChatReplyService)을 재사용하고, 실제 생성
호출만 core/lol의 LoraRecommendationOrchestrator(lora_server, 주기 재학습된
공용 LoRA 어댑터)로 교체한다.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from core.lol.lora_recommendation_orchestrator import (
    LoraOrchestratorError,
    LoraRecommendationOrchestrator,
)
from mova.adapter.inbound.api.schemas.market_chat_schema import (
    MovaChatRecommendationSchema,
)
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.adapter.outbound.llm.chat_prompt import ChatPromptBuilder
from mova.adapter.outbound.llm.chat_reply import ChatReplyService
from mova.adapter.outbound.llm.intent_extraction import IntentExtractionService
from mova.app.ports.output.llm_errors import LLMError
from mova.app.ports.output.llm_output_port import RecommendationPort


class LoraRecommendationAdapter(RecommendationPort):
    def __init__(self) -> None:
        self._intent_svc = IntentExtractionService()
        self._prompt_builder = ChatPromptBuilder()
        self._reply_svc = ChatReplyService()
        self._orchestrator = LoraRecommendationOrchestrator()

    def extract_intent(self, message: str) -> dict[str, Any]:
        return self._intent_svc.extract(message)

    async def generate_recommendation(
        self,
        *,
        history: list[dict[str, str]],
        message: str,
        intent: dict[str, Any],
        tag_catalog: list[MovaSearchItemSchema],
        past_intents: list,
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
        except LoraOrchestratorError as e:
            raise LLMError(e.detail, status_code=e.status_code) from e
        reply, recs = self._reply_svc.parse_gemini_reply(raw)
        recs = await self._reply_svc.enrich_from_db(recs, tag_catalog=tag_catalog)
        return reply, recs
