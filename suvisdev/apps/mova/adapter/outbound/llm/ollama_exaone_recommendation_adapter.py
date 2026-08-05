"""EXAONE-3.5-7.8B(Ollama) 추천 어댑터 — RecommendationPort 구현체.

QwenRecommendationAdapter와 완전히 동일한 구조지만, T1MidFakerOrchestrator를 기본
모델(exaone3.5:7.8b)로 사용한다. Qwen2.5-1.5B로 실측 비교한 결과(3회 반복), Qwen은
RAG로 검색된 실제 컨텍스트와 무관한 제목을 매번 지어냈고(할루시네이션), EXAONE은
컨텍스트에 없으면 정직하게 되묻거나 실제 검색 결과(예: "슈퍼걸")를 반영했다 —
추천 품질이 신뢰성에 직결되는 이 경로는 AWQ 직접 서빙(gptqmodel) 대신 Ollama
버전 EXAONE으로 되돌린다. VRAM도 Ollama가 알아서 순차 로드/언로드 하므로 문제없다.
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


class OllamaExaoneRecommendationAdapter(RecommendationPort):
    def __init__(self) -> None:
        self._intent_svc = IntentExtractionService()
        self._prompt_builder = ChatPromptBuilder()
        self._reply_svc = ChatReplyService()
        self._orchestrator = T1MidFakerOrchestrator()  # 기본값 = exaone3.5:7.8b

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
        recs = await self._reply_svc.enrich_from_db(recs, tag_catalog=tag_catalog)
        return reply, recs
