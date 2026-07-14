"""EXAONE(Router, Ollama) 추천 어댑터 — RecommendationPort 구현체.

GeminiRecommendationAdapter와 동일한 프롬프트·파싱 로직(ChatPromptBuilder·
ChatReplyService)을 재사용하고, 실제 생성 호출만 core/lol의 공용
오케스트레이터(exaone3.5:7.8b)로 교체한다.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from core.lol.t1_mid_faker_orchestrator import FakerOrchestratorError, T1MidFakerOrchestrator
from mova.adapter.inbound.api.schemas.market_chat_schema import (
    MovaChatRecommendationSchema,
)
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.adapter.outbound.llm.chat_prompt import ChatPromptBuilder
from mova.adapter.outbound.llm.chat_reply import ChatReplyService
from mova.adapter.outbound.llm.intent_extraction import IntentExtractionService
from mova.app.ports.output.llm_errors import LLMError
from mova.app.ports.output.llm_output_port import RecommendationPort

# mova 채팅은 picks 3편을 JSON으로 뽑아야 해서 Worker(2.4b)보다 판단력이
# 나은 Router(7.8b)를 쓴다 (dispatch/spam_filter 등 단순 자유 텍스트 spoke와는 다름).
_MOVA_CHAT_MODEL = "exaone3.5:7.8b"


class ExaoneRecommendationAdapter(RecommendationPort):
    def __init__(self) -> None:
        self._intent_svc = IntentExtractionService()
        self._prompt_builder = ChatPromptBuilder()
        self._reply_svc = ChatReplyService()
        self._orchestrator = T1MidFakerOrchestrator(model=_MOVA_CHAT_MODEL)

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
        except FakerOrchestratorError as e:
            raise LLMError(e.detail, status_code=e.status_code) from e
        reply, recs = self._reply_svc.parse_gemini_reply(raw)
        recs = await self._reply_svc.enrich_from_db(recs)
        return reply, recs
