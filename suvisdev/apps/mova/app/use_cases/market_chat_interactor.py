"""채팅 Interactor — ChatUseCase 구현체."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4

from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRequest
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.app.dtos.market_chat_dto import ChatRecommendationDto, ChatResponseDto
from mova.app.ports.input.market_chat_use_case import ChatUseCase
from mova.app.ports.output.llm_output_port import RecommendationPort
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort
from mova.app.ports.output.user_preference_query_port import UserPreferenceQueryPort
from ontology.app.dtos.mycroft_dto import MycroftAskCommand
from ontology.app.ports.input.hub_rag_use_case import HubRagUseCase
from ontology.app.ports.input.mycroft_use_case import MycroftUseCase
from ontology.app.ports.output.intent_classifier_port import IntentClassifierPort

logger = logging.getLogger(__name__)


class ChatInteractor(ChatUseCase):
    def __init__(
        self,
        repository: ChatRepositoryPort,
        recommender: RecommendationPort,
        preferences: UserPreferenceQueryPort,
        hub_rag: HubRagUseCase,
        classifier: IntentClassifierPort,
        general: MycroftUseCase,
    ) -> None:
        self._repo = repository
        self._llm = recommender
        self._preferences = preferences
        self._hub_rag = hub_rag
        self._classifier = classifier
        self._general = general

    async def chat(self, request: MovaChatRequest) -> ChatResponseDto:
        trace_id = uuid4().hex[:8]
        logger.info(
            "[ChatInteractor] trace=%s question 수신 len=%d", trace_id, len(request.message)
        )

        # 0. 시맨틱 인텐트 분류 — 영화와 무관한 잡담/일반 질문(general)은 RAG·추천
        #    파이프라인을 타지 않고 Gemini(Mycroft)로 바로 위임한다.
        destination, _entities = await self._classifier.classify(request.message)
        logger.info("[ChatInteractor] trace=%s destination=%s", trace_id, destination)
        if destination == "general":
            return await self._reply_general(request, trace_id)

        # 1. 의도 추출 (CPU-bound → 스레드 위임). LLM 출력 포트 경유.
        intent = await asyncio.to_thread(self._llm.extract_intent, request.message)

        # 2. RAG 시맨틱 검색(ontology Hub) + 사용자 컨텍스트 (병렬). 0건이면 기존 태그
        #    키워드 검색으로 폴백 — Hub/Ollama 임베딩 장애 시에도 채팅 자체는 계속 동작해야 한다.
        rag_query = intent["refined_query"] or request.message
        catalog_task = self._hub_rag.search_movies(rag_query, k=8, trace_id=trace_id)
        if request.user_id:
            intents_task = self._repo.get_recent_intents_by_user(request.user_id, limit=3)
            prefs_task = self._preferences.get_preferences(request.user_id)
            hits, past_intents, prefs = await asyncio.gather(
                catalog_task, intents_task, prefs_task
            )
            nickname, preferred_genres = prefs.nickname, prefs.preferred_genres
        else:
            hits = await catalog_task
            past_intents, nickname, preferred_genres = [], None, []

        if hits:
            catalog = [
                MovaSearchItemSchema(
                    id=h.source_ref,
                    title=h.title,
                    year="",
                    rating=0.0,
                    poster="",
                    match_type="semantic",
                )
                for h in hits
            ]
        else:
            logger.info("[ChatInteractor] trace=%s fallback search_tag_catalog 사용", trace_id)
            catalog = await self._repo.search_tag_catalog(intent["keywords"][:6], limit=12)

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
            "[ChatInteractor] trace=%s chat_id=%d intent=%s reply_chars=%d recs=%d",
            trace_id,
            chat_id,
            intent["intent_type"],
            len(reply),
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

    async def _reply_general(self, request: MovaChatRequest, trace_id: str) -> ChatResponseDto:
        """영화 지식 조회가 필요 없는 잡담 — RAG·추천 없이 Gemini(Mycroft) 답변만 저장·반환."""
        answer = await self._general.ask(MycroftAskCommand(question=request.message))
        chat_id = await self._repo.save_chat(
            user_id=request.user_id,
            assistant_id=None,
            raw_message=request.message,
            refined_query=request.message,
            keywords=[],
            intent_type="general",
            search_filters={},
        )
        logger.info(
            "[ChatInteractor] trace=%s chat_id=%d intent=general reply_chars=%d recs=0",
            trace_id,
            chat_id,
            len(answer.text),
        )
        return ChatResponseDto(
            chat_id=chat_id,
            reply=answer.text,
            refined_query=request.message,
            keywords=[],
            intent_type="general",
            search_filters={},
            recommendations=[],
        )
