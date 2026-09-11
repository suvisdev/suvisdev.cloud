"""채팅 Interactor — ChatUseCase 구현체."""

from __future__ import annotations

import asyncio
import logging
import math
import re
from datetime import UTC, datetime
from typing import Any
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
from mova.app.use_cases.market_chat_booking_interactor import (
    BookingAssistService,
    pending_title_from_history,
)
from mova.app.use_cases.market_chat_evaluation_interactor import MovieEvaluationService
from ontology.app.dtos.mycroft_dto import MycroftAskCommand
from ontology.app.ports.input.hub_rag_use_case import HubRagUseCase
from ontology.app.ports.input.mycroft_use_case import MycroftUseCase
from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.app.ports.output.intent_classifier_port import IntentClassifierPort

logger = logging.getLogger(__name__)

# rag 경로(ChatPromptBuilder.MOVA_SYSTEM_PROMPT)는 JSON 카드 강제용이라 general에
# 재사용하지 않는다 — general은 포맷 강제 없는 대화체 답변이 목적이다.
_GENERAL_CHAT_SYSTEM_PROMPT = (
    "너는 mova의 영화 대화 도우미다. 영화/작품 관련 일반 질문에 한국어로 간결하고 "
    "자연스럽게 답한다. 추천 요청이면 목록을 나열하지 말고 대화로 안내한다. "
    "[이전 대화]가 주어지면 그 흐름에 이어서 답하고, 사용자가 불만이나 지적을 "
    "하면 인사말 없이 짧게 사과한 뒤 어떻게 다시 요청하면 되는지 한 가지만 안내한다."
)

# 평가를 들은 뒤의 긍정 반응 — chat_trend 조건부 신호(2026-08-28 결정: 단순
# 질의는 미집계, 긍정 반응·예매 의지만 반영). 실측 사례가 쌓이면 보강한다.
_EVAL_POSITIVE_PATTERNS: tuple[str, ...] = (
    "볼래",
    "볼게",
    "봐야겠",
    "보고 싶",
    "보고싶",
    "재밌겠",
    "기대된다",
    "기대돼",
    "예매할래",
)

# 제목 없는 evaluate 후속("어때?"·"어떠냐고"·"그거 평가해줘")을 결정론으로 잡는다.
# 분류기가 이런 발화를 recommend로 오분류해 두루뭉술한 답이 나오던 것 대응
# (2026-09-09 실측). 트리거 어휘가 있고, 지시어·조사·트랙 어휘를 다 떼면 아무것도
# 안 남을 때만 "제목 없는 평가 요청"으로 본다 — "어벤져스 어때"는 '어벤져스'가 남아 제외.
_EVAL_TRIGGER_WORDS = re.compile(r"(어때|어떄|어떠|어떤|어떻|어떨|평가|평점|리뷰|볼만|괜찮)")
_EVAL_STRIP = re.compile(
    r"(그거|그건|이거|이건|저거|그영화|이영화|그작품|이작품|그|이|저|얘|걔"
    r"|은|는|이|가|을|를|에\s*대해서?|영화|작품"
    r"|어때|어떄|어떠[냐네]|어떤가|어떤지|어떰|어떻게|어떨까"
    r"|볼만해|볼만한[가지]|평가|평점|리뷰|괜찮아|괜찮은[가지]"
    r"|해줘|해|줘|주라|봐줘|봐|주세요|고|요|나요|가요|좀|한\s*번)"
)


def _is_bare_eval_followup(message: str) -> bool:
    m = message.strip()
    if not _EVAL_TRIGGER_WORDS.search(m):
        return False
    remainder = re.sub(r"[\s?!.~]", "", _EVAL_STRIP.sub("", m))
    return remainder == ""


def _last_assistant_content(history: list[dict[str, str]]) -> str:
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            return msg.get("content") or ""
    return ""


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
    recs: list[ChatRecommendationDto],
    taste_vector: list[float],
    embeddings_by_id: dict[int, list[float]],
) -> list[ChatRecommendationDto]:
    """recs를 taste vector와의 cosine 유사도(내림차순)로 재정렬.

    embedding이 없는(dict에 missing) rec은 cosine=-1로 취급해 뒤로 밀리지만,
    자기들 사이의 상대 순서는 원본을 유지(stable sort). 재정렬 대상이 3편
    수준이라 순수 Python으로 충분(pgvector <=>를 SQL로 태울 규모 아님).
    """

    def _key(rec_with_idx: tuple[int, Any]) -> tuple[float, int]:
        original_idx, rec = rec_with_idx
        vec = embeddings_by_id.get(getattr(rec, "movie_id", None))  # type: ignore[arg-type]
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
        evaluation: MovieEvaluationService | None = None,
        booking: BookingAssistService | None = None,
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
        # 3트랙(2026-08-28): 미주입이면 해당 destination도 기존 추천 경로로
        # 흘려 하위호환 유지(기존 테스트·부팅 경로 보호).
        self._evaluation = evaluation
        self._booking = booking

    async def chat(self, request: MovaChatRequest) -> ChatResponseDto:
        trace_id = uuid4().hex[:8]
        logger.info(
            "[ChatInteractor] trace=%s question 수신 len=%d", trace_id, len(request.message)
        )

        # -1. 대화 스레드 소유권 사전 검증(LLM 쿼터 소모 전에). 로그인 + 기존 id
        #     지정 시에만 조회. 없거나 남의 것이면 여기서 즉시 raise.
        await self._verify_conversation_ownership(request)

        # -0.5. booking 지역 이어받기 — 직전 assistant 응답이 지역 되묻기였으면
        #       이번 발화는 지역명이다. 분류기를 거치지 않고 결정론으로 잇는다
        #       ("강남" 단독 발화는 분류기가 general로 오분류하기 쉽다).
        if self._booking is not None:
            pending_title = pending_title_from_history(request.history_dicts())
            if pending_title:
                logger.info(
                    "[ChatInteractor] trace=%s booking 지역 이어받기 title=%s",
                    trace_id,
                    pending_title,
                )
                return await self._reply_booking(
                    request, trace_id, entities=[], pending_title=pending_title
                )

        # -0.4. evaluate 후속 이어받기 — 제목 없는 "어때?"류는 직전 assistant가 소개한
        #       영화를 평가한다. 분류기가 이런 발화를 recommend로 오분류해 근거 없는
        #       답이 나오던 것 방지(2026-09-09 실측: "어떠냐고" → recommendation).
        if self._evaluation is not None and _is_bare_eval_followup(request.message):
            last_movie = await self._repo.find_movie_titled_in_text(
                _last_assistant_content(request.history_dicts())
            )
            if last_movie is not None:
                logger.info(
                    "[ChatInteractor] trace=%s evaluate 후속 이어받기 title=%s",
                    trace_id,
                    last_movie.title,
                )
                return await self._reply_evaluation(request, trace_id, entities=[last_movie.title])

        # 0. 시맨틱 인텐트 분류(2026-08-28 5종: recommend/evaluate/booking/general/
        #    crud) — 영화와 무관한 잡담(general)은 추천 파이프라인을 타지 않고
        #    Gemini(Mycroft)로 바로 위임한다. mova/chat엔 실제 CRUD 기능이 없으므로
        #    (crud는 분류기가 가끔 오분류하는 잡음에 가깝다) general과 동일 처리.
        destination, entities = await self._classifier.classify(request.message)
        logger.info("[ChatInteractor] trace=%s destination=%s", trace_id, destination)

        # 평가 직후의 긍정 반응은 chat_trend 조건부 신호로 기록(발화 자체는
        # 원래 갈 곳으로 계속 흘린다 — 보통 general).
        await self._maybe_record_eval_positive(request, trace_id)

        if destination == "evaluate" and self._evaluation is not None:
            return await self._reply_evaluation(request, trace_id, entities)
        if destination == "booking" and self._booking is not None:
            return await self._reply_booking(
                request, trace_id, entities=entities, pending_title=None
            )
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
            _uid: int = request.user_id  # narrowed by `if request.user_id:` guard

            async def _user_context() -> tuple[list[Any], Any]:
                intents = await self._repo.get_recent_intents_by_user(_uid, limit=3)
                prefs = await self._preferences.get_preferences(_uid)
                return intents, prefs

            hits, (past_intents, prefs) = await asyncio.gather(catalog_task, _user_context())
            nickname, preferred_genres = prefs.nickname, prefs.preferred_genres
        else:
            hits = await catalog_task
            past_intents, nickname, preferred_genres = [], None, []

        search_wider = None  # RAG(semantic) 경로에는 풀 확장 재검색이 없다
        must = intent["search_filters"].get("must") or {}
        similar = intent["search_filters"].get("similar_to") or {}
        actor_names = [*must.get("actors", []), *similar.get("actors", [])]
        from mova.domain.value_objects.franchise_expansion import (
            expand_franchise_titles,
        )
        from mova.domain.value_objects.mood_expansion import expand_mood_keywords

        async def _search_tags(keywords: list[str], limit: int) -> list[MovaSearchItemSchema]:
            return await self._repo.search_tag_catalog(
                keywords,
                limit=limit,
                actor_names=actor_names,
                countries=must.get("countries") or [],
                year_min=intent["search_filters"].get("year_min"),
                year_max=intent["search_filters"].get("year_max"),
                # "마블" 같은 프랜차이즈 언급 → 대표작 제목 매칭 (2026-08-25)
                title_terms=expand_franchise_titles(intent["keywords"]),
            )

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
            # RAG 히트는 hub에 연도 메타데이터가 없어 연도 하드 필터를 못
            # 지킨다(2026-09-03 "클래식 명작 처음 보는 사람용" 실사고,
            # trace=f4552cee: year_max=1999 요청에 시맨틱 tail의 2003·2007년작이
            # 유입돼 LoRA가 그쪽을 픽 → '식객' 무관 추천). 연도 조건이 있으면
            # 히트의 movie_id를 movies.release_year로 재검증해 위반을 제거한다.
            # 연도 조건이 없는 질의(좀비 등)는 이 경로를 아예 안 탄다.
            year_min = intent["search_filters"].get("year_min")
            year_max = intent["search_filters"].get("year_max")
            if year_min is not None or year_max is not None:
                hit_ids = [int(c.id) for c in catalog if str(c.id).isdigit()]
                valid_ids = await self._repo.filter_movie_ids_by_year(hit_ids, year_min, year_max)
                before = len(catalog)
                catalog = [c for c in catalog if str(c.id).isdigit() and int(c.id) in valid_ids]
                if len(catalog) != before:
                    logger.info(
                        "[ChatInteractor] trace=%s RAG 연도 필터 %d→%d편 (%s~%s)",
                        trace_id,
                        before,
                        len(catalog),
                        year_min or "",
                        year_max or "",
                    )
            # RAG 히트가 태그 실매칭을 가리는 갭(2026-09-01 실측, trace=81b08f57):
            # "좀비 영화"처럼 태그가 실재해도 시맨틱이 무관 히트를 물어오면 태그
            # 검색을 아예 안 타 recs=0이 됐다. 시맨틱 히트가 있어도 태그 검색을
            # 함께 돌려 실매칭이 있으면 합집합(캡 16)으로 후보를 넓힌다.
            # 순서는 태그 실매칭 우선 — 결정론 신호(키워드·배우·제목 매칭)가
            # 시맨틱 저유사 히트보다 정확하고, 2.4B LoRA가 목록 앞쪽 후보에
            # 끌리는 것을 프로덕션에서 실측(2026-09-02: RAG 우선 순서일 때
            # 좀비 태그 후보를 두고 무관 시맨틱 1편을 픽). mood 확장은 여기선
            # 안 쓴다 — 순수 mood 질의는 태그 실매칭이 없어 popular_fallback으로
            # 떨어지고, 그건 버려서 현행(RAG 단독)이 유지된다.
            tag_items = await _search_tags(intent["keywords"], 16)
            # 연도·국가 하드 필터가 있으면 popular_fallback도 실후보로 인정한다
            # (2026-09-02 "최신영화 알려줘" 실사고): hub에 연도 메타데이터가 없어
            # 시맨틱 히트는 하드 필터를 못 지키는데("최신"→"작년에 봤던 새" 매칭),
            # popular_fallback은 그 조건을 SQL로 만족한 인기작이다. mood 질의는
            # 하드 필터가 없어 현행(RAG 단독)이 그대로 유지된다.
            filters = intent["search_filters"]
            has_hard_filter = (
                bool(must.get("countries"))
                or filters.get("year_min") is not None
                or filters.get("year_max") is not None
            )
            real_matches = [
                t for t in tag_items if t.match_type != "popular_fallback" or has_hard_filter
            ]
            if real_matches:
                head = real_matches[:10]  # 시맨틱 보충 여지를 남기는 상한
                head_ids = {t.id for t in head}
                catalog = (head + [c for c in catalog if c.id not in head_ids])[:16]
                logger.info(
                    "[ChatInteractor] trace=%s RAG+태그 합집합 후보 %d편(태그 %s)",
                    trace_id,
                    len(catalog),
                    real_matches[0].match_type,
                )
        else:
            logger.info("[ChatInteractor] trace=%s fallback search_tag_catalog 사용", trace_id)
            # mood 자연어("오싹오싹한" 등)를 대중 장르 태그로 확장 (2026-08-13).
            # Ollama 임베딩이 안 붙는 환경에서 tag catalog 폴백이 mood를 이해하도록.
            expanded_keywords = expand_mood_keywords(intent["keywords"])[:12]

            async def _search_catalog(limit: int) -> list[MovaSearchItemSchema]:
                return await _search_tags(expanded_keywords, limit)

            search_wider = _search_catalog  # dedup 소진 시 재검색용 (폴백 경로만)
            catalog = await _search_catalog(16)

        # 2.5. 대화 스레드에서 이미 추천한 영화 슬러그를 뽑아 후보에서 제거한다.
        #      "다른 것도 추천해줘" 같은 후속 질의에서 같은 영화 재소개 방지.
        already_shown_slugs = await self._recently_recommended_slugs(request)
        if already_shown_slugs:
            filtered = [c for c in catalog if c.id not in already_shown_slugs]
            if not filtered and search_wider is not None:
                # dedup 소진 대안 행동(2026-08-26, 실측 zero-rec 13건 중 4건이
                # 이 케이스): 조건은 그대로 두고 후보 풀만 16→48로 넓혀 한 번
                # 재검색한다. 그래도 새 후보가 없으면 기존 동작(원본 유지 →
                # LLM 정직한 0카드)으로 떨어진다.
                wider = await search_wider(48)
                filtered = [c for c in wider if c.id not in already_shown_slugs][:16]
                if filtered:
                    logger.info(
                        "[ChatInteractor] trace=%s dedup 소진 → 풀 확장 재검색으로 새 후보 %d편",
                        trace_id,
                        len(filtered),
                    )
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
        recs = await self._rerank_recommendations(request.user_id, recs, trace_id)  # type: ignore[arg-type,assignment]

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
        self, user_id: int | None, recs: list[ChatRecommendationDto], trace_id: str
    ) -> list[ChatRecommendationDto]:
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
        embeddings_by_id = await self._movies.list_embeddings_by_ids(movie_ids)  # type: ignore[arg-type]
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

    async def _reply_evaluation(
        self, request: MovaChatRequest, trace_id: str, entities: list[str]
    ) -> ChatResponseDto:
        """evaluate 트랙 — 서비스가 만든 평가를 저장·응답 형태로 감싼다."""
        assert self._evaluation is not None
        result = await self._evaluation.evaluate(
            message=request.message, entities=entities, trace_id=trace_id
        )
        chat_id = await self._repo.save_chat(
            user_id=request.user_id,
            assistant_id=None,
            raw_message=request.message,
            refined_query=request.message,
            keywords=entities,
            intent_type="evaluate",
            search_filters={},
        )
        recommendations = [result.card] if result.card else []
        assistant_meta: dict[str, Any] = {"recommendations": self._cards_meta(recommendations)}
        if result.evaluation is not None:
            # movie_id는 다음 턴의 긍정 반응 신호(_maybe_record_eval_positive)가,
            # 나머지 payload는 스레드 복원 시 프론트 지표 패널 재구성이 쓴다.
            assistant_meta["evaluation"] = {
                "movie_id": result.evaluation.movie_id,
                "review_count": result.evaluation.review_count,
                "avg_rating": result.evaluation.avg_rating,
                "tmdb_rating": result.evaluation.tmdb_rating,
                "excerpts": result.evaluation.excerpts,
            }
        conversation_id = await self._persist_conversation_turn(
            request=request,
            user_content=request.message,
            user_meta={
                "intent_type": "evaluate",
                "refined_query": request.message,
                "keywords": entities,
            },
            assistant_content=result.reply,
            assistant_meta=assistant_meta,
        )
        logger.info(
            "[ChatInteractor] trace=%s chat_id=%d intent=evaluate status=%s",
            trace_id,
            chat_id,
            result.status,
        )
        return ChatResponseDto(
            chat_id=chat_id,
            reply=result.reply,
            refined_query=request.message,
            keywords=entities,
            intent_type="evaluate",
            search_filters={},
            recommendations=recommendations,
            conversation_id=conversation_id,
            response_type="evaluation",
            evaluation=result.evaluation,
            choices=result.candidates,
        )

    async def _reply_booking(
        self,
        request: MovaChatRequest,
        trace_id: str,
        *,
        entities: list[str],
        pending_title: str | None,
    ) -> ChatResponseDto:
        """booking 트랙 — 상영 여부·지역 슬롯 필링·영화관 안내."""
        assert self._booking is not None
        result = await self._booking.assist(
            message=request.message,
            entities=entities,
            trace_id=trace_id,
            pending_title=pending_title,
            # 지역-선행 발화("군자쪽에 예매…")의 맥락 영화 역조회용(2026-09-11)
            history=request.history_dicts(),
        )
        # 예매 의지 신호(chat_trend 조건부 반영) — 작품이 확정된 최초 턴에서만,
        # 로그인 사용자 한정(user_actions.user_id NOT NULL).
        if request.user_id and result.resolved_movie_id and pending_title is None:
            await self._repo.record_user_action(
                request.user_id, result.resolved_movie_id, "booking_intent"
            )
        chat_id = await self._repo.save_chat(
            user_id=request.user_id,
            assistant_id=None,
            raw_message=request.message,
            refined_query=request.message,
            keywords=entities,
            intent_type="booking",
            search_filters={},
        )
        recommendations = [result.card] if result.card else []
        assistant_meta: dict[str, Any] = {"recommendations": self._cards_meta(recommendations)}
        if result.booking is not None:
            # 스레드 복원 시 프론트 영화관 패널 재구성용.
            assistant_meta["booking"] = {
                "status": result.booking.status,
                "region": result.booking.region,
                "theaters": [
                    {
                        "name": t.name,
                        "address": t.address,
                        "distance_m": t.distance_m,
                        "place_url": t.place_url,
                        "phone": t.phone,
                    }
                    for t in result.booking.theaters
                ],
                "booking_links": [
                    {"chain": link.chain, "url": link.url} for link in result.booking.booking_links
                ],
                "showtimes": [
                    {
                        "cinema_name": cs.cinema_name,
                        "slots": [
                            {
                                "screen": s.screen,
                                "start_time": s.start_time,
                                "end_time": s.end_time,
                                "film_type": s.film_type,
                                "seats_available": s.seats_available,
                                "seats_total": s.seats_total,
                            }
                            for s in cs.slots
                        ],
                    }
                    for cs in result.booking.showtimes
                ],
            }
        conversation_id = await self._persist_conversation_turn(
            request=request,
            user_content=request.message,
            user_meta={
                "intent_type": "booking",
                "refined_query": request.message,
                "keywords": entities,
            },
            assistant_content=result.reply,
            assistant_meta=assistant_meta,
        )
        logger.info(
            "[ChatInteractor] trace=%s chat_id=%d intent=booking status=%s booking=%s",
            trace_id,
            chat_id,
            result.status,
            result.booking.status if result.booking else "-",
        )
        return ChatResponseDto(
            chat_id=chat_id,
            reply=result.reply,
            refined_query=request.message,
            keywords=entities,
            intent_type="booking",
            search_filters={},
            recommendations=recommendations,
            conversation_id=conversation_id,
            response_type="booking",
            booking=result.booking,
        )

    @staticmethod
    def _cards_meta(cards: list[ChatRecommendationDto]) -> list[dict[str, Any]]:
        return [
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
            for r in cards
        ]

    async def _maybe_record_eval_positive(self, request: MovaChatRequest, trace_id: str) -> None:
        """직전 assistant 턴이 평가였고 이번 발화가 긍정 반응이면 chat_trend 신호 기록."""
        if not (request.user_id and request.conversation_id and self._conversations):
            return
        if not any(p in request.message for p in _EVAL_POSITIVE_PATTERNS):
            return
        movie_id = await self._conversations.get_last_evaluation_movie_id(request.conversation_id)
        if movie_id is None:
            return
        await self._repo.record_user_action(request.user_id, movie_id, "eval_positive")
        logger.info(
            "[ChatInteractor] trace=%s eval_positive 신호 기록 movie_id=%d",
            trace_id,
            movie_id,
        )

    async def _reply_general(self, request: MovaChatRequest, trace_id: str) -> ChatResponseDto:
        """영화 지식 조회가 필요 없는 잡담 — RAG·추천 없이 Gemini(Mycroft) 답변만 저장·반환."""
        # 최근 대화를 함께 넘긴다 — 없으면 "똑같은 말 반복하지마" 같은 불만에
        # 맥락 없는 인사말이 나간다(2026-08-26 라이브 실측). Mycroft 포트가
        # question+system만 받으므로 히스토리는 질문 텍스트에 인라인한다.
        history = request.history_dicts()[-6:]
        if history:
            context = "\n".join(
                f"{'사용자' if m['role'] == 'user' else '도우미'}: {m['content'][:200]}"
                for m in history
                if m["content"]
            )
            question = f"[이전 대화]\n{context}\n\n[현재 발화]\n{request.message}"
        else:
            question = request.message
        # LLM 장애·쿼터 429가 500으로 새지 않게 정직한 안내로 강등한다
        # (2026-09-03 실측: "안녕" → Gemini 429 → HubRagError 미포착 → 500).
        # 추천 트랙은 LoRA+폴백 체인이 받지만 general은 이 호출이 유일한 경로다.
        try:
            answer = await self._general.ask(
                MycroftAskCommand(question=question, system=_GENERAL_CHAT_SYSTEM_PROMPT)
            )
            reply_text = answer.text
        except HubRagError as e:
            logger.warning(
                "[ChatInteractor] trace=%s general LLM 실패 → 정직 안내 강등 | %s",
                trace_id,
                e.detail,
            )
            reply_text = (
                "지금 대화 응답이 혼잡해서 잠시 답변이 어려워요. "
                "조금 뒤에 다시 말을 걸어주시거나, 원하는 영화 분위기를 알려주시면 추천은 바로 도와드릴 수 있어요."
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
            len(reply_text),
        )
        conversation_id = await self._persist_conversation_turn(
            request=request,
            user_content=request.message,
            user_meta={"intent_type": "general", "refined_query": request.message, "keywords": []},
            assistant_content=reply_text,
            assistant_meta={"recommendations": []},
        )
        return ChatResponseDto(
            chat_id=chat_id,
            reply=reply_text,
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
        user_meta: dict[str, Any],
        assistant_content: str,
        assistant_meta: dict[str, Any],
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
        await self._conversations.append_message(conversation_id, "user", user_content, user_meta)
        await self._conversations.append_message(
            conversation_id, "assistant", assistant_content, assistant_meta
        )
        return conversation_id
