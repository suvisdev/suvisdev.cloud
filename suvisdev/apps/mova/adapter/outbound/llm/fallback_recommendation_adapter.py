"""추천 폴백 데코레이터 — primary(LoRA) 실패 시 fallback(Gemini)으로 자동 전환.

RECOMMENDATION_BACKEND=lora일 때 lora 서버가 꺼져 있으면 예전엔 배포 환경
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

# 실매칭 후보가 이만큼 있는데 0편이면 LoRA 오답으로 본다(3편 미만은 정직한 0편일 수 있다).
_MIN_REAL_CANDIDATES_FOR_RETRY = 3


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
        kwargs: dict[str, Any] = dict(
            history=history,
            message=message,
            intent=intent,
            tag_catalog=tag_catalog,
            past_intents=past_intents,
            user_nickname=user_nickname,
            preferred_genres=preferred_genres,
            model=model,
        )
        try:
            reply, recs = await self._primary.generate_recommendation(**kwargs)
        except LLMError as e:
            logger.warning(
                "[FallbackRecommendationAdapter] primary 실패(%s) — fallback으로 전환",
                e.detail,
            )
            return await self._fallback.generate_recommendation(**kwargs)
        # 실매칭 후보가 충분한데 0편 — LoRA가 가끔 그러는 결정적 오답("법정 드라마 영화",
        # 2026-09-22·09-27 실측: 후보 16편에 recs=0). 에러가 아니라 폴백이 안 걸리던 구멍이라
        # 한 번 더 fallback(Gemini)에 맡긴다. 인기작 폴백뿐인 후보는 0편이 정직한 답이라 제외.
        real = [c for c in tag_catalog if c.match_type != "popular_fallback"]
        if not recs and len(real) >= _MIN_REAL_CANDIDATES_FOR_RETRY:
            logger.warning(
                "[FallbackRecommendationAdapter] primary가 후보 %d편에서 0편 — fallback 재시도",
                len(real),
            )
            try:
                f_reply, f_recs = await self._fallback.generate_recommendation(**kwargs)
            except LLMError as e:
                logger.warning("[FallbackRecommendationAdapter] fallback도 실패(%s)", e.detail)
                return reply, recs
            if f_recs:
                return f_reply, f_recs
        return reply, recs
