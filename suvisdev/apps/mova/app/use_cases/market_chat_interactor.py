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

# rag 경로(ChatPromptBuilder.MOVA_SYSTEM_PROMPT)는 JSON 카드 강제용이라 general에
# 재사용하지 않는다 — general은 포맷 강제 없는 대화체 답변이 목적이다.
_GENERAL_CHAT_SYSTEM_PROMPT = (
    "너는 mova의 영화 대화 도우미다. 영화/작품 관련 일반 질문에 한국어로 간결하고 "
    "자연스럽게 답한다. 추천 요청이면 목록을 나열하지 말고 대화로 안내한다."
)


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
        #    파이프라인을 타지 않고 Gemini(Mycroft)로 바로 위임한다. mova/chat엔 실제
        #    CRUD 기능이 없으므로(crud는 분류기가 가끔 오분류하는 잡음에 가깝다),
        #    영화 추천 파이프라인으로 잘못 흘려보내는 대신 general과 동일하게 처리한다.
        destination, _entities = await self._classifier.classify(request.message)
        logger.info("[ChatInteractor] trace=%s destination=%s", trace_id, destination)
        if destination in ("general", "crud"):
            return await self._reply_general(request, trace_id)

        # 1. 의도 추출 (CPU-bound → 스레드 위임). LLM 출력 포트 경유.
        intent = await asyncio.to_thread(self._llm.extract_intent, request.message)

        # 2. RAG 시맨틱 검색(ontology Hub) + 사용자 컨텍스트 (병렬). 0건이면 기존 태그
        #    키워드 검색으로 폴백 — Hub/Ollama 임베딩 장애 시에도 채팅 자체는 계속 동작해야 한다.
        rag_query = intent["refined_query"] or request.message
        catalog_task = self._hub_rag.search_movies(rag_query, k=8, trace_id=trace_id)
        if request.user_id:
            # self._repo·self._preferences는 둘 다 get_mova_db() 세션을 공유하므로
            # (FastAPI가 요청당 Depends 결과를 캐싱) 서로 동시에 돌리면 SQLAlchemy가
            # "concurrent operations are not permitted"로 막는다 — 순차 실행으로 묶는다.
            async def _user_context() -> tuple[list, object]:
                intents = await self._repo.get_recent_intents_by_user(request.user_id, limit=3)
                prefs = await self._preferences.get_preferences(request.user_id)
                return intents, prefs

            hits, (past_intents, prefs) = await asyncio.gather(catalog_task, _user_context())
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
            must = intent["search_filters"].get("must") or {}
            similar = intent["search_filters"].get("similar_to") or {}
            actor_names = [*must.get("actors", []), *similar.get("actors", [])]
            catalog = await self._repo.search_tag_catalog(
                intent["keywords"][:6], limit=16, actor_names=actor_names
            )

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
        answer = await self._general.ask(
            MycroftAskCommand(question=request.message, system=_GENERAL_CHAT_SYSTEM_PROMPT)
        )
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
