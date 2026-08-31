"""추천 폴백 데코레이터 — primary(LoRA) 실패 시 fallback(Gemini)으로 자동 전환.

RECOMMENDATION_BACKEND=lora일 때 노트북 lora 서버가 꺼져 있으면 예전엔 EC2
`.env`를 고쳐 컨테이너를 재생성해야 했다(수동 폴백, 2026-08-25 실측 왕복 8초 +
사람 개입). 이 데코레이터가 LLMError를 잡아 fallback으로 넘기므로 수동 전환이
필요 없어진다. 서킷 브레이커(core/lol)가 열려 있으면 primary는 HTTP 호출 없이
즉시 실패하므로 폴백 지연도 없다.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from mova.adapter.inbound.api.schemas.market_chat_schema import (
    MovaChatRecommendationSchema,
)
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.app.ports.output.llm_errors import LLMError
from mova.app.ports.output.llm_output_port import RecommendationPort

logger = logging.getLogger(__name__)


class FallbackRecommendationAdapter(RecommendationPort):
    def __init__(self, primary: RecommendationPort, fallback: RecommendationPort) -> None:
        self._primary = primary
        self._fallback = fallback

    def extract_intent(
        self, message: str, history: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        # 의도 추출은 두 어댑터 모두 동일한 IntentExtractionService라 폴백 불필요.
        return self._primary.extract_intent(message, history=history)

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
        try:
            return await self._primary.generate_recommendation(
                history=history,
                message=message,
                intent=intent,
                tag_catalog=tag_catalog,
                past_intents=past_intents,
                user_nickname=user_nickname,
                preferred_genres=preferred_genres,
                model=model,
            )
        except LLMError as e:
            logger.warning(
                "[FallbackRecommendationAdapter] primary 실패(%s) — fallback으로 전환",
                e.detail,
            )
            return await self._fallback.generate_recommendation(
                history=history,
                message=message,
                intent=intent,
                tag_catalog=tag_catalog,
                past_intents=past_intents,
                user_nickname=user_nickname,
                preferred_genres=preferred_genres,
                model=model,
            )
