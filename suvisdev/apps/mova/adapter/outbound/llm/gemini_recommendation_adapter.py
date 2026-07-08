"""Gemini 추천 어댑터 — RecommendationPort 구현체.

기존 llm/ 서비스(IntentExtractionService · ChatPromptBuilder · ChatReplyService ·
gemini_reply)를 출력 포트 뒤로 래핑한다. Interactor가 구체 LLM 클래스를 직접
import 하지 않도록 하는 것이 목적이다 (DIP).
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from mova.adapter.inbound.api.schemas.market_chat_schema import (
    MovaChatRecommendationSchema,
)
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.adapter.outbound.llm.chat_prompt import ChatPromptBuilder
from mova.adapter.outbound.llm.chat_reply import ChatReplyService
from mova.adapter.outbound.llm.gemini_client import gemini_reply
from mova.adapter.outbound.llm.intent_extraction import IntentExtractionService
from mova.app.ports.output.llm_output_port import RecommendationPort


class GeminiRecommendationAdapter(RecommendationPort):
    def __init__(self) -> None:
        self._intent_svc = IntentExtractionService()
        self._prompt_builder = ChatPromptBuilder()
        self._reply_svc = ChatReplyService()

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
        # Gemini SDK는 블로킹 호출 → 스레드 위임
        raw = await asyncio.to_thread(gemini_reply, prompt, model)
        reply, recs = self._reply_svc.parse_gemini_reply(raw)
        recs = await self._reply_svc.enrich_from_db(recs)
        return reply, recs
