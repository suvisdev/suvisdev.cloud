"""채팅 Interactor — ChatUseCase 구현체."""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import UTC, datetime
from uuid import uuid4

from mova.adapter.inbound.api.schemas.market_chat_schema import MovaChatRequest
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.app.dtos.market_chat_dto import ChatRecommendationDto, ChatResponseDto
from mova.app.ports.input.market_chat_use_case import ChatUseCase
from mova.app.ports.output.llm_output_port import RecommendationPort
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort
from mova.app.ports.output.market_conversations_errors import (
    ConversationForbiddenError,
    ConversationNotFoundError,
)
from mova.app.ports.output.market_conversations_repository import ConversationsRepository
from mova.app.ports.output.movies_repository import MoviesRepositoryPort
from mova.app.ports.output.platform_user_taste_vector_repository import (
    UserTasteVectorRepositoryPort,
)
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


def _cosine(a: list[float], b: list[float]) -> float:
    """0벡터·차원 불일치는 0.0 반환 — 재정렬에서 그 rec만 뒤로 밀려남."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _rerank_by_taste_cosine(
    recs: list,
    taste_vector: list[float],
    embeddings_by_id: dict[int, list[float]],
) -> list:
    """recs를 taste vector와의 cosine 유사도(내림차순)로 재정렬.

    embedding이 없는(dict에 missing) rec은 cosine=-1로 취급해 뒤로 밀리지만,
    자기들 사이의 상대 순서는 원본을 유지(stable sort). 재정렬 대상이 3편
    수준이라 순수 Python으로 충분(pgvector <=>를 SQL로 태울 규모 아님).
    """
    def _key(rec_with_idx: tuple[int, object]) -> tuple[float, int]:
        original_idx, rec = rec_with_idx
        vec = embeddings_by_id.get(getattr(rec, "movie_id", None))
        if vec is None:
            # embedding 없는 rec은 재정렬 대상 밖 — 뒤로. 큰 key로 밀되
            # 자기들끼리는 original_idx로 원래 순서 유지.
            return (math.inf, original_idx)
        # cosine 내림차순 = -cosine 오름차순.
        return (-_cosine(taste_vector, vec), original_idx)

    indexed = list(enumerate(recs))
    indexed.sort(key=_key)
    return [rec for _, rec in indexed]


class ChatInteractor(ChatUseCase):
    def __init__(
        self,
        repository: ChatRepositoryPort,
        recommender: RecommendationPort,
        preferences: UserPreferenceQueryPort,
        hub_rag: HubRagUseCase,
        classifier: IntentClassifierPort,
        general: MycroftUseCase,
        conversations: ConversationsRepository | None = None,
        movies: MoviesRepositoryPort | None = None,
        taste_vectors: UserTasteVectorRepositoryPort | None = None,
    ) -> None:
        self._repo = repository
        self._llm = recommender
        self._preferences = preferences
        self._hub_rag = hub_rag
        self._classifier = classifier
        self._general = general
        # 대화 스레드는 로그인 사용자 한정 저장. 없어도 챗 자체는 동작해야 하므로
        # optional 주입 — 테스트나 초기 부팅 경로에서 미주입이어도 크래시 안 남.
        self._conversations = conversations
        # 취향 벡터 재정렬은 로그인 유저 + 리뷰 임베딩이 준비된 유저에게만 적용.
        # 두 port 중 하나라도 미주입이면 재정렬 스킵(LLM 원 순서 유지). 기존
        # 테스트가 두 인자 없이 인스턴스화해도 깨지지 않게 optional로 둔다.
        self._movies = movies
        self._taste_vectors = taste_vectors

    async def chat(self, request: MovaChatRequest) -> ChatResponseDto:
        trace_id = uuid4().hex[:8]
        logger.info(
            "[ChatInteractor] trace=%s question 수신 len=%d", trace_id, len(request.message)
        )

        # -1. 대화 스레드 소유권 사전 검증(LLM 쿼터 소모 전에). 로그인 + 기존 id
        #     지정 시에만 조회. 없거나 남의 것이면 여기서 즉시 raise.
        await self._verify_conversation_ownership(request)

        # 0. 시맨틱 인텐트 분류 — 영화와 무관한 잡담/일반 질문(general)은 RAG·추천
        #    파이프라인을 타지 않고 Gemini(Mycroft)로 바로 위임한다. mova/chat엔 실제
        #    CRUD 기능이 없으므로(crud는 분류기가 가끔 오분류하는 잡음에 가깝다),
        #    영화 추천 파이프라인으로 잘못 흘려보내는 대신 general과 동일하게 처리한다.
        destination, _entities = await self._classifier.classify(request.message)
        logger.info("[ChatInteractor] trace=%s destination=%s", trace_id, destination)
        if destination in ("general", "crud"):
            return await self._reply_general(request, trace_id)

        # 1. 의도 추출 (CPU-bound → 스레드 위임). LLM 출력 포트 경유.
        # 대화 히스토리를 함께 넘겨 후속 발화("최근영화로")가 이전 조건("코미디")을
        # 삼키지 않게 한다 — 각 턴이 독립 추천이 되던 문제 대응(2026-08-14).
        intent = await asyncio.to_thread(
            self._llm.extract_intent, request.message, request.history_dicts()
        )

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
            # mood 자연어("오싹오싹한" 등)를 대중 장르 태그로 확장 (2026-08-13).
            # Ollama 임베딩이 안 붙는 환경에서 tag catalog 폴백이 mood를 이해하도록.
            from mova.domain.value_objects.franchise_expansion import (
                expand_franchise_titles,
            )
            from mova.domain.value_objects.mood_expansion import expand_mood_keywords

            expanded_keywords = expand_mood_keywords(intent["keywords"])[:12]
            catalog = await self._repo.search_tag_catalog(
                expanded_keywords,
                limit=16,
                actor_names=actor_names,
                countries=must.get("countries") or [],
                year_min=intent["search_filters"].get("year_min"),
                year_max=intent["search_filters"].get("year_max"),
                # "마블" 같은 프랜차이즈 언급 → 대표작 제목 매칭 (2026-08-25)
                title_terms=expand_franchise_titles(intent["keywords"]),
            )

        # 2.5. 대화 스레드에서 이미 추천한 영화 슬러그를 뽑아 후보에서 제거한다.
        #      "다른 것도 추천해줘" 같은 후속 질의에서 같은 영화 재소개 방지.
        already_shown_slugs = await self._recently_recommended_slugs(request)
        if already_shown_slugs:
            filtered = [c for c in catalog if c.id not in already_shown_slugs]
            if filtered:  # 전부 필터되면(후보 부족) 원본 유지 — LLM이 정직하게 0카드 응답
                dropped = len(catalog) - len(filtered)
                if dropped > 0:
                    logger.info(
                        "[ChatInteractor] trace=%s 중복 제거 후 후보 %d→%d (이미 소개 %d편)",
                        trace_id,
                        len(catalog),
                        len(filtered),
                        len(already_shown_slugs),
                    )
                catalog = filtered

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

        # 3.5. 취향 벡터 재정렬 — 로그인 유저 + taste vector·movies embedding
        #      양쪽 준비된 경우에만. 후보 생성/enrich 결과 순서는 LLM이 정한
        #      것이지 별점순이 아니므로, 개인화 신호가 있으면 그 안에서 순서를
        #      다시 잡는다. 재정렬 후 순서로 save_picks까지 반영해 UI 카드
        #      배치와 저장 순서가 일치하게 한다. 별점 결합(alpha 튜닝)은
        #      별도 백로그.
        recs = await self._rerank_recommendations(request.user_id, recs, trace_id)

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

        # 2차 안전망 — 후보 필터가 완벽하지 않아도(LLM이 카탈로그 밖 자유 응답,
        # slug 오해 등) 최종 반환에서 한 번 더 이미 소개한 영화를 제거.
        if already_shown_slugs:
            recs = [r for r in recs if r.id not in already_shown_slugs]

        # 추천할 영화가 실제로 0건이면 reply 텍스트도 그에 맞춰 정직하게 안내.
        # LLM이 "추천해 드릴게요"라고 말해놓고 카드가 안 뜨는 어긋남 방지.
        # 문구를 문자열 하나로 고정하면 사용자가 재시도할수록 같은 답이 반복돼 UX 저하
        # (2026-08-13 실측: "뭔 영화가 이렇게 없냐" · "똑같은 말 반복하지마" 재시도에도
        # 같은 문구가 그대로 돌아옴). 아래처럼 다양화하고, 이미 소개한 게 많으면
        # 실제로 아직 안 본 인기 상위 3편을 안내에 인라인한다.
        if not recs:
            already_len = len(already_shown_slugs) if already_shown_slugs else 0
            reply = await self._compose_empty_reply(
                user_id=request.user_id,
                already_shown_slugs=already_shown_slugs or set(),
                retry_after_shown=already_len > 0,
            )

        recommendation_dtos = [
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
        ]
        conversation_id = await self._persist_conversation_turn(
            request=request,
            user_content=request.message,
            user_meta={
                "intent_type": intent["intent_type"],
                "refined_query": intent["refined_query"],
                "keywords": intent["keywords"],
            },
            assistant_content=reply,
            assistant_meta={
                "recommendations": [
                    {
                        "id": r.id,
                        "movie_id": r.movie_id,
                        "title": r.title,
                        "year": r.year,
                        "poster": r.poster,
                        "synopsis": r.synopsis,
                        "platform": r.platform,
                        "hook": r.hook,
                    }
                    for r in recommendation_dtos
                ],
            },
        )
        return ChatResponseDto(
            chat_id=chat_id,
            reply=reply,
            refined_query=intent["refined_query"],
            keywords=intent["keywords"],
            intent_type=intent["intent_type"],
            search_filters=intent["search_filters"],
            recommendations=recommendation_dtos,
            conversation_id=conversation_id,
        )

    async def _rerank_recommendations(
        self, user_id: int | None, recs: list, trace_id: str
    ) -> list:
        """taste vector가 있으면 movies.embedding과의 cosine으로 recs 재정렬.

        스킵 조건(전부 debug 로그만): 비로그인, 두 port 중 하나 미주입,
        taste vector 없음(리뷰 0건/rating 합계 0), recs 비어 있음, 모든
        rec의 embedding이 dict에 없음(전량 unknown).
        """
        if not recs:
            return recs
        if user_id is None:
            logger.debug("[ChatInteractor] trace=%s rerank skip: 비로그인", trace_id)
            return recs
        if self._taste_vectors is None or self._movies is None:
            logger.debug(
                "[ChatInteractor] trace=%s rerank skip: taste/movies port 미주입", trace_id
            )
            return recs

        taste_vector = await self._taste_vectors.get_taste_vector(user_id)
        if taste_vector is None:
            logger.debug(
                "[ChatInteractor] trace=%s rerank skip: taste vector 없음(user=%d)",
                trace_id,
                user_id,
            )
            return recs

        movie_ids = [r.movie_id for r in recs if getattr(r, "movie_id", None) is not None]
        embeddings_by_id = await self._movies.list_embeddings_by_ids(movie_ids)
        if not embeddings_by_id:
            logger.debug(
                "[ChatInteractor] trace=%s rerank skip: movies.embedding 전량 없음", trace_id
            )
            return recs

        reranked = _rerank_by_taste_cosine(recs, taste_vector, embeddings_by_id)
        logger.info(
            "[ChatInteractor] trace=%s rerank 적용 user=%d recs=%d embedded=%d",
            trace_id,
            user_id,
            len(recs),
            len(embeddings_by_id),
        )
        return reranked

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
        conversation_id = await self._persist_conversation_turn(
            request=request,
            user_content=request.message,
            user_meta={"intent_type": "general", "refined_query": request.message, "keywords": []},
            assistant_content=answer.text,
            assistant_meta={"recommendations": []},
        )
        return ChatResponseDto(
            chat_id=chat_id,
            reply=answer.text,
            refined_query=request.message,
            keywords=[],
            intent_type="general",
            search_filters={},
            recommendations=[],
            conversation_id=conversation_id,
        )

    async def _compose_empty_reply(
        self, *, user_id: int | None, already_shown_slugs: set[str], retry_after_shown: bool
    ) -> str:
        """추천 0건 안내 문구. 문자열 하나로 고정하면 재시도마다 같은 답이 반복돼
        사용자 인지의 "봇 반복" 문제를 유발 — 여러 변형에서 랜덤 pick하고, 재시도로
        보이면 조금 더 구체적인 대안(장르 예시)까지 붙인다.

        인라인 영화 3편 실제 추천은 별도 후속 스코프.
        """
        import random

        # 이미 소개한 게 많으면 "새 작품이 없다"고 알리고 대안 축을 다양하게 제시.
        with_shown = [
            "이 대화에서 아직 소개하지 않은 새 작품 중엔 해당 조건에 딱 맞는 게 없네요. "
            "다른 장르(스릴러·다큐·애니메이션 등)나 '요즘 인기작' 같은 표현으로 다시 물어봐 주세요.",
            "이번 조건으로는 새로 추천할 영화가 카탈로그에 안 남아 있어요. "
            "배우 이름을 하나 더하거나 '90년대 클래식' 같은 시대 필터를 붙여보시면 반응이 달라져요.",
            "여기까지 소개한 목록 외엔 새 후보가 안 나오네요. "
            "OTT(넷플릭스·티빙 등)나 '가족과 볼만한' 같은 상황을 붙여 다시 요청하면 다른 결과가 나올 수 있어요.",
        ]
        cold = [
            "지금 카탈로그에서 조건에 맞는 영화를 못 찾았어요. "
            "장르·배우·연도를 하나만 바꿔 다시 요청해 주시면 다시 찾아볼게요.",
            "요청하신 조건과 겹치는 작품이 카탈로그에 없어요. "
            "예: '감성 로맨스', '20세기 폭스 클래식', 'A24 스릴러' 같은 방식으로 다시 물어봐 주세요.",
            "이 조건에는 매칭되는 작품이 안 잡히네요. "
            "'국내 개봉 SF', '넷플릭스에서 볼 수 있는 코미디'처럼 플랫폼·나라를 함께 알려주시면 도움이 됩니다.",
        ]
        pool = with_shown if retry_after_shown else cold
        _ = user_id, already_shown_slugs  # 시그니처는 유지(추후 개인화·인라인 추천 확장 여지)
        return random.choice(pool)

    async def _recently_recommended_slugs(self, request: MovaChatRequest) -> set[str]:
        """대화 스레드에서 이전에 소개한 영화 슬러그 집합. 스레드 없거나 conversations
        포트 미주입이면 빈 집합."""
        if not (request.user_id and request.conversation_id and self._conversations):
            return set()
        try:
            return await self._conversations.get_recent_recommendation_slugs(
                request.conversation_id, limit=30
            )
        except Exception:
            # 필터 조회 실패는 조용히 스킵 — 채팅 자체는 계속 동작해야 함.
            return set()

    async def _verify_conversation_ownership(self, request: MovaChatRequest) -> None:
        """LLM 호출 전에 대화 소유권 확인. 로그인+id 지정 케이스에만 검사."""
        if not (request.user_id and request.conversation_id and self._conversations):
            return
        owner_id = await self._conversations.get_owner_id(request.conversation_id)
        if owner_id is None:
            raise ConversationNotFoundError()
        if owner_id != request.user_id:
            raise ConversationForbiddenError()

    async def _persist_conversation_turn(
        self,
        *,
        request: MovaChatRequest,
        user_content: str,
        user_meta: dict,
        assistant_content: str,
        assistant_meta: dict,
    ) -> int | None:
        """로그인 사용자에 한해 대화 스레드에 user+assistant 두 메시지 append.
        conversation_id가 없으면 새 스레드 생성(title = 첫 user 메시지 앞 40자).
        conversations 포트 미주입이거나 비로그인이면 None."""
        if not (request.user_id and self._conversations):
            return None
        conversation_id = request.conversation_id
        if conversation_id is None:
            title = user_content.strip().splitlines()[0][:40] if user_content.strip() else "새 대화"
            conversation_id = await self._conversations.create(request.user_id, title)
        await self._conversations.append_message(
            conversation_id, "user", user_content, user_meta
        )
        await self._conversations.append_message(
            conversation_id, "assistant", assistant_content, assistant_meta
        )
        return conversation_id
