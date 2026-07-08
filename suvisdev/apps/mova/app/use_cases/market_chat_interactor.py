"""채팅 Interactor — ChatUseCase 구현체."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRequest
from mova.app.dtos.market_chat_dto import ChatRecommendationDto, ChatResponseDto
from mova.app.ports.input.market_chat_use_case import ChatUseCase
from mova.app.ports.output.llm_output_port import RecommendationPort
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort
from mova.app.ports.output.user_preference_query_port import UserPreferenceQueryPort

logger = logging.getLogger(__name__)


class ChatInteractor(ChatUseCase):
    def __init__(
        self,
        repository: ChatRepositoryPort,
        recommender: RecommendationPort,
        preferences: UserPreferenceQueryPort,
    ) -> None:
        self._repo = repository
        self._llm = recommender
        self._preferences = preferences

    async def chat(self, request: MovaChatRequest) -> ChatResponseDto:
        # 1. 의도 추출 (CPU-bound → 스레드 위임). LLM 출력 포트 경유.
        intent = await asyncio.to_thread(self._llm.extract_intent, request.message)

        # 2. 태그 카탈로그 검색 + 사용자 컨텍스트 (병렬)
        catalog_task = self._repo.search_tag_catalog(intent["keywords"][:6], limit=12)
        if request.user_id:
            intents_task = self._repo.get_recent_intents_by_user(request.user_id, limit=3)
            prefs_task = self._preferences.get_preferences(request.user_id)
            catalog, past_intents, prefs = await asyncio.gather(
                catalog_task, intents_task, prefs_task
            )
            nickname, preferred_genres = prefs.nickname, prefs.preferred_genres
        else:
            catalog = await catalog_task
            past_intents, nickname, preferred_genres = [], None, []

        # 3. 추천 생성 (프롬프트·Gemini·파싱·DB 보강은 포트 구현체 내부)
        reply, recs = await self._llm.generate_recommendation(
            history=request.history_dicts(),
            message=request.message,
            intent=intent,
            tag_catalog=catalog,
            past_intents=past_intents,
            user_nickname=nickname,
            preferred_genres=preferred_genres,
            model=request.model,
        )

        # 4. chat + picks 저장
        batch_at = datetime.now(UTC)
        chat_id = await self._repo.save_chat(
            user_id=request.user_id,
            assistant_id=None,
            raw_message=request.message,
            refined_query=intent["refined_query"],
            keywords=intent["keywords"],
            intent_type=intent["intent_type"],
            search_filters=intent["search_filters"],
        )
        await self._repo.save_picks(
            chat_id=chat_id,
            user_id=request.user_id,
            recommendations=recs,
            batch_at=batch_at,
        )

        logger.info(
            "[ChatInteractor] chat_id=%d intent=%s recs=%d",
            chat_id,
            intent["intent_type"],
            len(recs),
        )
        return ChatResponseDto(
            chat_id=chat_id,
            reply=reply,
            refined_query=intent["refined_query"],
            keywords=intent["keywords"],
            intent_type=intent["intent_type"],
            search_filters=intent["search_filters"],
            recommendations=[
                ChatRecommendationDto(
                    id=r.id,
                    movie_id=r.movie_id,
                    title=r.title,
                    year=r.year,
                    poster=r.poster,
                    synopsis=r.synopsis,
                    platform=r.platform,
                    hook=r.hook,
                )
                for r in recs
            ],
        )
