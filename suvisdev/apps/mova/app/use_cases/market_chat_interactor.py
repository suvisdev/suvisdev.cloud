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
from mova.app.dtos.chat_understanding_dto import VerifiedSlots
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
from mova.app.use_cases.chat_agent import MovaChatAgent, compose_facts, wants_review_summary
from mova.app.use_cases.chat_orchestrator import ChatOrchestrator
from mova.app.use_cases.market_chat_booking_interactor import (
    BookingAssistService,
    BookingResult,
    _extract_region_signal,
    pending_title_from_history,
)
from mova.app.use_cases.market_chat_evaluation_interactor import MovieEvaluationService
from mova.app.use_cases.market_chat_ordinal import resolve_ordinal_reference
from mova.domain.value_objects.movie_title import MovieTitle, series_key
from ontology.app.agent.agent_loop import AgentDecision
from ontology.app.dtos.mycroft_dto import MycroftAskCommand
from ontology.app.ports.input.hub_rag_use_case import HubRagUseCase
from ontology.app.ports.input.mycroft_use_case import MycroftUseCase
from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.app.ports.output.intent_classifier_port import IntentClassifierPort
from ontology.app.ports.output.judge_port import JudgeError

logger = logging.getLogger(__name__)

# rag 경로(ChatPromptBuilder.MOVA_SYSTEM_PROMPT)는 JSON 카드 강제용이라 general에
# 재사용하지 않는다 — general은 포맷 강제 없는 대화체 답변이 목적이다.
_GENERAL_CHAT_SYSTEM_PROMPT = (
    "너는 mova의 영화 대화 도우미다. 영화/작품 관련 일반 질문에 한국어로 간결하고 "
    "자연스럽게 답한다. 추천 요청이면 목록을 나열하지 말고 대화로 안내한다. "
    "[이전 대화]가 주어지면 그 흐름에 이어서 답하고, 사용자가 불만이나 지적을 "
    "하면 인사말 없이 짧게 사과한 뒤 어떻게 다시 요청하면 되는지 한 가지만 안내한다. "
    # 2026-09-27 실사용: 시간표 질의가 이 트랙으로 새자 '롯데시네마 군자점 14:10·17:30'을
    # 지어냈다. 이 트랙은 극장·시간표를 조회하지 않는다 — 조회는 예매 도우미(booking)가
    # 카카오 지도 극장 검색 + 롯데시네마 시간표로 한다. 그러니 "모른다"로 끝내지 말고
    # 그쪽으로 넘기는 말을 하되, 절대 지어내지 않는다.
    "상영 시간표·회차·영화관 지점·예매 가능 여부는 이 대화에서 조회하지 못하므로 절대 "
    "추측하거나 지어내지 않는다. 대신 '작품명과 함께 예매 또는 시간표를 말씀해 주시면 "
    "근처 영화관과 롯데시네마 상영 시간표를 찾아드린다'고 한 문장으로 안내한다. "
    "[지금 상영 중] 목록이 주어지면 그 목록에 있는 작품(괄호는 개봉 연도)만 현재 극장에서 "
    "상영 중이라고 말할 수 있고, 같은 제목이 여러 해에 있으면 목록의 연도를 따른다."
)

# 예매·시간표 어휘가 든 발화는 분류기 결과와 무관하게 booking 트랙으로 보낸다 —
# 분류기가 "인턴 영화 시간표 보여줘"를 general로 넘겨 Gemini가 시간표를 지어냈다
# (2026-09-27 실사용). booking은 시간표를 모르면 체인 검색 링크로 위임하므로 안전하다.
# '추천'이 섞인 발화("영화관에서 볼만한 거 추천")는 추천 트랙 몫이라 제외한다.
_BOOKING_LEXICON = re.compile(
    r"시간표|상영\s*(?:시간|회차|스케줄)|예매|예약|상영관|상영\s*중|회차"
    # 영화관·극장·지점·체인 언급은 그 자체로 예매 문맥이다(카카오 지도 극장 검색이 답한다).
    # "영화관에서 볼만한 거 추천"류는 아래 '추천' 제외로 추천 트랙에 남는다.
    r"|영화관|극장|지점|체인|어디서\s*(?:봐|볼|해|하)"
    # 체인명 — "군자에 롯데시네마가 있어?"(2026-09-27 실사용)
    r"|CGV|씨지브이|롯데시네마|메가박스"
    # "인턴 몇 시에 해?"·"오늘 몇 시에 볼 수 있어?" — 시간표 질문의 구어형(09-27 라이브 확인).
    # '몇 시간짜리'는 제외(시간≠시각).
    r"|몇\s*시(?!간)"
)
_RECOMMEND_WORD = re.compile(r"추천")


def _is_booking_lexicon(message: str) -> bool:
    return bool(_BOOKING_LEXICON.search(message)) and not _RECOMMEND_WORD.search(message)


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


# 제목이 있는 줄거리 요청("기생충 줄거리 알려줘")을 결정론으로 evaluate에 보낸다.
# 분류기(LLM)가 이런 발화를 recommend로 보내 줄거리 대신 비슷한 영화를 추천하던 것 대응
# (2026-09-22 실사용). 추천 어휘가 같이 있으면("줄거리 반전 있는 영화 추천") 추천 요청이다.
_SYNOPSIS_WORDS = re.compile(
    r"(줄거리|시놉시스|(무슨|어떤)\s*내용|내용\s*(이|을|좀)?\s*(뭐|알려|설명))"
)
_RECOMMEND_WORDS = re.compile(r"(추천|비슷한|같은\s*영화|볼\s*만한)")


def _is_synopsis_request(message: str) -> bool:
    return bool(_SYNOPSIS_WORDS.search(message)) and not _RECOMMEND_WORDS.search(message)


_MIN_VOTES = 30  # MOVA_RECOMMENDATION_CRITERIA §2-2
_MIN_SOLID_CANDIDATES = 5


def _quality_floor(catalog: list[MovaSearchItemSchema]) -> list[MovaSearchItemSchema]:
    """투표 _MIN_VOTES 이상이 _MIN_SOLID_CANDIDATES편 이상이면 미만(0=미수집 포함)을 빼고,
    모자라면 뒤로만 보낸다(안정 정렬 — 나머지 순서는 그대로).

    뒤로만 보내는 방식은 효과가 없었다(2026-09-28 실측 low_vote 6→7): 분위기 질의는 시맨틱
    후보가 8편이라 전부 프롬프트에 실리고, LoRA가 뒤쪽 작품도 고른다. 사용자 결정으로 제외로 강화.
    """
    solid = [c for c in catalog if c.vote_count >= _MIN_VOTES]
    if len(solid) >= _MIN_SOLID_CANDIDATES:
        return solid
    return sorted(catalog, key=lambda c: c.vote_count < _MIN_VOTES)


def _one_per_series(catalog: list[MovaSearchItemSchema]) -> list[MovaSearchItemSchema]:
    """시리즈마다 앞선 후보 하나만 — 3편이 한 시리즈로 몰리지 않게(추천 기준 §2-3).

    2026-09-28 하네스: "마동석 액션"→범죄도시·범죄도시 3, "형사물"→나쁜 녀석들·포에버.
    """
    seen: set[str] = set()
    out: list[MovaSearchItemSchema] = []
    for c in catalog:
        key = series_key(c.title)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


_PERSONAL_CUE = re.compile(
    r"내\s?취향|나한테\s?맞|나에게\s?맞|내가\s?본|내\s?리뷰|내\s?별점|취향(에|대로|껏)|맞춤"
)
_BARE_RECOMMEND = re.compile(
    r"^(영화\s*)?(추천(\s*해\s*줘|해\s*주세요|\s*좀)?|뭐\s*볼까\??|볼\s*거\s*(추천\s*)?(좀|줘)?|오늘\s*뭐\s*보지\??)\s*[!?~.]*$"
)
_SIMILAR_TO = re.compile(
    r"^(.+?)\s*(?:와|과|랑|이랑|하고)?\s*(같은|비슷한|비슷하게|느낌의?|류의?)\s*(영화|작품|거)"
)


def taste_query_vector(
    ratings: list[tuple[int, float]], embeddings: dict[int, list[float]]
) -> list[float] | None:
    """높게 평가한 영화일수록 크게(별점-2.5, 최소 0.25) 가중한 영화 임베딩 평균. 임베딩 없으면 None."""
    acc: list[float] | None = None
    total = 0.0
    for movie_id, rating in ratings:
        vec = embeddings.get(movie_id)
        if not vec:
            continue
        w = max(rating - 2.5, 0.25)
        acc = (
            [w * x for x in vec]
            if acc is None
            else [a + w * x for a, x in zip(acc, vec, strict=True)]
        )
        total += w
    return [x / total for x in acc] if acc and total > 0 else None


def personal_recommend_cue(message: str) -> tuple[str | None, str | None]:
    """("similar", 시드 제목) | ("taste", None) | (None, None). 조건 추천과 구분되는 두 신호(2026-09-29):
    "기생충 같은 영화" → 시드 작품 유사, "내 취향에 맞는 거"·맨 "추천해줘" → 취향 벡터."""
    m = (message or "").strip()
    sim = _SIMILAR_TO.match(m)
    if sim and len(sim.group(1).strip()) >= 2:
        return "similar", sim.group(1).strip()
    if _PERSONAL_CUE.search(m) or _BARE_RECOMMEND.match(m):
        return "taste", None
    return None, None


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


# 후보 제시 문구는 evaluate/booking 트랙이 결정론으로 만든다(ambiguous 분기) —
# 그 형식("제목(연도) / …")을 그대로 되읽어 다음 턴의 선택을 잇는다.
_CHOICE_PREFIX = "비슷한 제목이 여러 편이에요: "
_CHOICE_ENTRY = re.compile(r"^(.*?)(?:\((\d{4})\))?$")
_CHOICE_YEAR4 = re.compile(r"(?<!\d)(\d{4})(?!\d)")
_CHOICE_YEAR2 = re.compile(r"(?<!\d)(\d{2})\s*년")
_CHOICE_ORDINALS = (
    ("첫", "1번", "하나"),
    ("두번째", "둘째", "두 번째", "2번"),
    ("세번째", "셋째", "세 번째", "3번"),
)
_CHOICE_TAIL = re.compile(r"(말하는거잖아|말하는거|꺼|거|것|영화|작품|으로|로|이요|요)+[\s?!.~]*$")


def pick_from_choice_list(last_assistant: str, message: str) -> tuple[str, str] | None:
    """직전 응답이 후보 제시였고 이번 발화가 그중 하나를 고르면 (제목, 트랙)을 돌려준다.

    트랙은 되묻기 꼬리로 구분한다("예매하시려나요" → booking, 그 외 → evaluate).
    연도(2026·"26년")·순서("두번째")·제목 부분일치 중 정확히 하나만 잡힐 때 확정한다 —
    둘 이상이면 None(되묻기 유지)이 잘못 짚는 것보다 낫다.
    """
    if not last_assistant.startswith(_CHOICE_PREFIX):
        return None
    body = last_assistant[len(_CHOICE_PREFIX) :]
    body = body.split(". 어떤 작품", 1)[0]
    entries: list[tuple[str, str | None]] = []
    for raw in body.split(" / "):
        m = _CHOICE_ENTRY.match(raw.strip())
        if m and m.group(1).strip():
            entries.append((m.group(1).strip(), m.group(2)))
    if not entries:
        return None
    track = "booking" if "예매하시려나요" in last_assistant else "evaluate"

    text = message.strip()
    matched: list[str] = []
    year: str | None = None
    if m4 := _CHOICE_YEAR4.search(text):
        year = m4.group(1)
    elif m2 := _CHOICE_YEAR2.search(text):
        yy = int(m2.group(1))
        year = str(2000 + yy if yy <= 30 else 1900 + yy)
    if year:
        matched = [t for t, y in entries if y == year]
    if not matched:
        for idx, words in enumerate(_CHOICE_ORDINALS):
            if any(w in text for w in words) and idx < len(entries):
                matched = [entries[idx][0]]
                break
    if not matched:
        needle = re.sub(r"\s+", "", _CHOICE_TAIL.sub("", text)).lower()
        if len(needle) >= 2:
            matched = [t for t, _ in entries if needle in re.sub(r"\s+", "", t).lower()]
    return (matched[0], track) if len(matched) == 1 else None


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
        orchestrator: ChatOrchestrator | None = None,
        agent: MovaChatAgent | None = None,
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
        # 오케스트레이터(2026-09-27): 발화를 EXAONE으로 한 번 이해하고 카탈로그로 검증한 뒤
        # 트랙을 고른다. 미주입·이해 실패면 아래 결정론 선분기 + 분류기 경로가 그대로 돈다.
        self._orchestrator = orchestrator
        # 에이전트(2026-09-29, v9): 판단 모델이 도구 호출로 다음 행동을 고른다. 주입되면 6칸 오케스트레이터보다
        # 먼저 시도하고, 판단 모델 장애(JudgeError)면 아래 경로로 폴백한다. 플래그 MOVA_CHAT_AGENT.
        self._agent = agent

    async def chat(self, request: MovaChatRequest) -> ChatResponseDto:
        trace_id = uuid4().hex[:8]
        logger.info(
            "[ChatInteractor] trace=%s question 수신 len=%d", trace_id, len(request.message)
        )
        # -2. 서수 지시어("두번째꺼")를 직전 추천 카드 제목으로 치환 — 이후 모든 경로가 제목을 본다.
        rewritten = resolve_ordinal_reference(request.message, request.history_dicts())
        if rewritten:
            logger.info(
                "[ChatInteractor] trace=%s 서수 치환 %r → %r", trace_id, request.message, rewritten
            )
            request = request.model_copy(update={"message": rewritten})

        # -1. 대화 스레드 소유권 사전 검증(LLM 쿼터 소모 전에). 로그인 + 기존 id
        #     지정 시에만 조회. 없거나 남의 것이면 여기서 즉시 raise.
        await self._verify_conversation_ownership(request)

        # -0.7. 에이전트(v9) — 판단 모델이 도구를 골라 돌리고, 사실은 템플릿·트랙이 답한다.
        if self._agent is not None:
            try:
                decision = await self._agent.decide(
                    request.message, request.history_dicts(), trace_id=trace_id
                )
            except JudgeError as e:
                logger.warning(
                    "[ChatInteractor] trace=%s 에이전트 판단 실패 → 이해 단계 폴백 | %s",
                    trace_id,
                    e.detail,
                )
            else:
                return await self._act_on_agent(request, trace_id, decision)

        # -0.6. 오케스트레이터 — 이해(LLM) → 검증(카탈로그) → 디스패치. 성공하면 아래
        #       결정론 선분기·분류기를 타지 않는다(같은 발화를 두 번 읽지 않는다).
        if self._orchestrator is not None:
            slots = await self._orchestrator.plan(
                request.message, request.history_dicts(), trace_id=trace_id
            )
            if slots is not None:
                return await self._dispatch_slots(request, trace_id, slots)

        # -0.5. booking 지역 이어받기 — 직전 assistant 응답이 지역 되묻기였으면
        #       이번 발화는 지역명이다. 분류기를 거치지 않고 결정론으로 잇는다
        #       ("강남" 단독 발화는 분류기가 general로 오분류하기 쉽다).
        if self._booking is not None:
            pending_title = pending_title_from_history(request.history_dicts())
            # 화제 전환 방어(2026-09-22 실사용: 지역 되묻기 뒤 "옵세션 줄거리 알려줘"가
            # 지역명으로 들어가 "'옵세션 줄거리 알려줘' 지역을 찾지 못했어요"). 발화가
            # 카탈로그 제목을 담고 지명 신호가 없으면 지역 답이 아니라 새 요청이다.
            if (
                pending_title
                and _extract_region_signal(request.message) is None
                and await self._repo.find_movie_titled_in_text(request.message) is not None
            ):
                logger.info(
                    "[ChatInteractor] trace=%s booking 대기 중 화제 전환 → 분류기로", trace_id
                )
                pending_title = None
            if pending_title:
                logger.info(
                    "[ChatInteractor] trace=%s booking 지역 이어받기 title=%s",
                    trace_id,
                    pending_title,
                )
                return await self._reply_booking(
                    request, trace_id, entities=[], pending_title=pending_title
                )

        # -0.45. 후보 제시("비슷한 제목이 여러 편이에요: A(2021) / B(2026)…") 뒤의 선택
        #        발화("26년꺼"·"두번째"·"브랜뉴데이")를 결정론으로 잇는다. 분류기로 가면
        #        "26년꺼"가 recommend로 흘러 "26년차 작품"으로 오해했다(2026-09-22 실사용).
        choice = pick_from_choice_list(
            _last_assistant_content(request.history_dicts()), request.message
        )
        if choice is not None:
            title, track = choice
            logger.info(
                "[ChatInteractor] trace=%s 후보 선택 이어받기 title=%s track=%s",
                trace_id,
                title,
                track,
            )
            if track == "booking" and self._booking is not None:
                return await self._reply_booking(
                    request, trace_id, entities=[title], pending_title=None
                )
            if track == "evaluate" and self._evaluation is not None:
                return await self._reply_evaluation(request, trace_id, entities=[title])

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
        if self._booking is not None and _is_booking_lexicon(request.message):
            logger.info("[ChatInteractor] trace=%s booking 어휘 선분기(분류기 생략)", trace_id)
            return await self._reply_booking(request, trace_id, entities=[], pending_title=None)

        # 0-a. 제목 있는 줄거리 요청은 evaluate(시놉시스 선행 규칙)로 — 분류기가 recommend로
        #      오분류하던 발화. 제목이 카탈로그에 없으면 그대로 분류기에 맡긴다.
        if self._evaluation is not None and _is_synopsis_request(request.message):
            movie = await self._repo.find_movie_titled_in_text(request.message)
            if movie is not None:
                logger.info(
                    "[ChatInteractor] trace=%s 줄거리 선분기(분류기 생략) title=%s",
                    trace_id,
                    movie.title,
                )
                return await self._reply_evaluation(request, trace_id, entities=[movie.title])

        destination, entities = await self._classifier.classify(request.message)
        logger.info(
            "[ChatInteractor] trace=%s destination=%s entities=%s", trace_id, destination, entities
        )

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

        return await self._reply_recommend(request, trace_id)

    async def _reply_recommend(self, request: MovaChatRequest, trace_id: str) -> ChatResponseDto:
        """추천 트랙 본문(무변경) — 의도 추출→RAG→후보→LLM→재정렬→저장."""
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
            # 제목뿐인 히트를 DB 카탈로그 아이템(연도·장르·줄거리·투표 수)으로 채운다 —
            # 프롬프트에 "연도 미상"으로만 실리면 LLM이 제목만 보고 고르고(2026-09-28 "비 오는 날"
            # →"비와 당신의 이야기"), 품질 하한도 판정할 수 없다. DB에 없는 히트는 그대로 둔다.
            described = {
                c.id: c
                for c in await self._repo.get_catalog_items(
                    [int(c.id) for c in catalog if str(c.id).isdigit()]
                )
            }
            catalog = [described.get(c.id, c) for c in catalog]
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
                # 배우 매칭이 받쳐주는 질의는 시맨틱 꼬리를 섞지 않는다 — DB 출연작이
                # 24~36편이라 결정론 후보만으로 상한(16)이 차고, 꼬리를 남기면 LoRA가
                # 미출연작을 고른다(2026-09-22 실측: "송강호 나오는 영화"에 궁합·
                # 천년여우 구미호 — DB 확인 결과 둘 다 송강호 미출연).
                if real_matches[0].match_type in ("actor", "actor+keyword"):
                    catalog = real_matches[:16]
                else:
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
        # 2.6. 로그인 사용자가 "봤어요"로 표시한 영화도 같은 제외 집합에 넣는다 — 본 영화를
        #      또 추천하지 않는다(2026-09-28 사용자: "본 거 또 볼 순 없잖아"). 아래 dedup
        #      소진·재검색·최종 recs 필터가 그대로 이 집합을 쓴다.
        already_shown_slugs = already_shown_slugs | await self._watched_slugs(request)
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

        # 2.7. 품질 하한 — 투표 30 이상이 충분하면 미만을 빼고, 모자라면 뒤로(MOVA_RECOMMENDATION_CRITERIA §2-2).
        catalog = _quality_floor(catalog)
        # 2.8. 다양성 — 시리즈를 직접 원한 요청("○○ 시리즈", 프랜차이즈 제목 매칭)은 제외.
        wants_series = "시리즈" in request.message or any(c.match_type == "title" for c in catalog)
        if not wants_series:
            catalog = _one_per_series(catalog)

        return await self._finish_recommend(
            request,
            trace_id,
            intent=intent,
            catalog=catalog,
            past_intents=past_intents,
            nickname=nickname,
            preferred_genres=preferred_genres,
            already_shown_slugs=already_shown_slugs,
        )

    async def _finish_recommend(
        self,
        request: MovaChatRequest,
        trace_id: str,
        *,
        intent: dict[str, Any],
        catalog: list[MovaSearchItemSchema],
        past_intents: list[Any],
        nickname: str | None,
        preferred_genres: list[str],
        already_shown_slugs: set[str],
    ) -> ChatResponseDto:
        """후보 목록 → LLM 픽 → 취향 재정렬 → 저장 → 응답. 조건 추천(`_reply_recommend`)과
        취향·유사 추천(`_reply_personal_recommend`)이 공유한다(2026-09-29 분리)."""
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
            reply=reply,
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

    async def _reply_personal_recommend(
        self, request: MovaChatRequest, trace_id: str, *, seed_title: str | None
    ) -> ChatResponseDto:
        """취향·유사 추천(2026-09-29, 원래 목적 "본 영화·리뷰·평점을 종합해 비슷한 영화"):
        - seed_title이 있으면 그 작품과 임베딩이 가까운 영화(`find_similar_movies`)를 후보로.
        - 없으면 로그인 유저의 취향 벡터(리뷰 임베딩의 별점 가중 평균)로 movies.embedding 최근접 후보.
        후보가 안 나오면(비로그인·리뷰 없음·미주입) 조건 추천으로 폴백. 본 영화·기추천은 제외."""
        already = await self._recently_recommended_slugs(request)
        already = already | await self._watched_slugs(request)
        ids: list[int] = []
        label, intent_type = "", "recommend"
        if seed_title and self._movies is not None:
            seed = await self._verify_agent_title(seed_title)
            detail = await self._movies.find_by_id(int(seed.id)) if seed is not None else None
            if detail is not None:
                similar = await self._movies.find_similar_movies(detail.slug, 24) or []
                ids = [int(m.id) for m in similar]
                label, intent_type = f"{detail.title}와 비슷한 영화", "similar"
        elif request.user_id and self._taste_vectors is not None and self._movies is not None:
            ratings = await self._taste_vectors.list_user_ratings(request.user_id)
            reviewed = {mid for mid, _ in ratings}
            emb = await self._movies.list_embeddings_by_ids(list(reviewed)) if reviewed else {}
            # 리뷰 문장 임베딩 평균(저장된 취향 벡터)은 줄거리 공간과 어긋나 후보가 흐릿했다(09-29 실측:
            # 주토피아·헤일메리 취향에 "지구를 지켜라") → 높게 평가한 영화들의 임베딩을 별점 가중 평균한다.
            query_vec = taste_query_vector(
                ratings, emb
            ) or await self._taste_vectors.get_taste_vector(request.user_id)
            if query_vec:
                skip = {
                    int(x) for x in already if str(x).isdigit()
                } | reviewed  # 리뷰한 영화 = 본 영화
                ids = await self._movies.find_nearest_by_vector(query_vec, 40, skip)
                label, intent_type = "내 리뷰·별점 취향 기반", "taste"
        if not ids:
            logger.info("[ChatInteractor] trace=%s 취향/유사 후보 없음 → 조건 추천", trace_id)
            return await self._reply_recommend(request, trace_id)
        catalog = [c for c in await self._repo.get_catalog_items(ids) if c.id not in already][:16]
        catalog = _one_per_series(_quality_floor(catalog))
        past_intents: list[Any] = []
        nickname, preferred_genres = None, []
        if request.user_id:
            past_intents = await self._repo.get_recent_intents_by_user(request.user_id, limit=3)
            prefs = await self._preferences.get_preferences(request.user_id)
            nickname, preferred_genres = prefs.nickname, prefs.preferred_genres
        logger.info(
            "[ChatInteractor] trace=%s %s 후보 %d편(제외 %d)",
            trace_id,
            intent_type,
            len(catalog),
            len(already),
        )
        intent = {
            "refined_query": label,
            "keywords": [],
            "intent_type": intent_type,
            "search_filters": {},
        }
        return await self._finish_recommend(
            request,
            trace_id,
            intent=intent,
            catalog=catalog,
            past_intents=past_intents,
            nickname=nickname,
            preferred_genres=preferred_genres,
            already_shown_slugs=already,
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

    async def _act_on_agent(
        self, request: MovaChatRequest, trace_id: str, decision: AgentDecision
    ) -> ChatResponseDto:
        """에이전트 결과 실행. 터미널 행동(추천·시간표·OTT)은 기존 트랙에 슬롯으로 넘기고, 데이터 도구로
        끝났으면 사실 템플릿(출연진·상영작·검색)이나 평가 트랙(리뷰 요약)이 답한다. 도구가 없으면 잡담."""
        if decision.terminal is not None:
            name, args = decision.terminal["name"], decision.terminal["arguments"]
            if name == "recommend_movies":
                mode, seed = personal_recommend_cue(request.message)
                if mode is not None:
                    logger.info(
                        "[ChatInteractor] trace=%s 취향/유사 추천 mode=%s seed=%r",
                        trace_id,
                        mode,
                        seed,
                    )
                    return await self._reply_personal_recommend(request, trace_id, seed_title=seed)
            title = args.get("title")
            movie = await self._verify_agent_title(title)
            slots = VerifiedSlots(
                intent="recommend" if name == "recommend_movies" else "booking",
                title_text=title,
                movie=movie,
                region=args.get("region"),
                time=args.get("date"),
                chain=None,
                followup=False,
            )
            logger.info(
                "[ChatInteractor] trace=%s 에이전트 터미널 %s → %s", trace_id, name, slots.intent
            )
            return await self._dispatch_slots(request, trace_id, slots)
        review_title = wants_review_summary(request.message, decision.results)
        if review_title and self._evaluation is not None:
            return await self._reply_evaluation(request, trace_id, [review_title])
        facts = compose_facts(request.message, decision.results)
        if facts is None:
            mode, seed = personal_recommend_cue(request.message)
            if (
                mode is not None
            ):  # v9가 맨 "추천해줘"를 잡담으로 볼 때가 있다 — 단서가 있으면 취향 추천
                return await self._reply_personal_recommend(request, trace_id, seed_title=seed)
            return await self._reply_general(request, trace_id)
        # 현재 상영작 질문("최신 개봉영화 뭐 있어", "다 영화관에서 볼 수 있어?")은 문장만이 아니라
        # 박스오피스 상영작을 카탈로그 카드로 붙인다 — 예매 트랙 성격이라 intent는 booking.
        cards: list[ChatRecommendationDto] = []
        intent_type = "info"
        if any(
            r["name"] == "now_showing" and "error" not in (r.get("result") or {})
            for r in decision.results
        ):
            intent_type = "booking"
            for d in await self._agent.showing_cards():
                cards.append(
                    ChatRecommendationDto(
                        id=d.slug,
                        movie_id=int(d.id),
                        title=d.title,
                        year=str(d.release_year or ""),
                        poster=d.poster_url or "",
                        synopsis=d.synopsis or "",
                        platform=d.platforms[0].provider if d.platforms else None,
                        hook="지금 상영 중(주간 박스오피스)",
                    )
                )
        chat_id = await self._repo.save_chat(
            user_id=request.user_id,
            assistant_id=None,
            raw_message=request.message,
            refined_query=request.message,
            keywords=[],
            intent_type=intent_type,
            search_filters={},
            reply=facts,
        )
        conversation_id = await self._persist_conversation_turn(
            request=request,
            user_content=request.message,
            user_meta={
                "intent_type": intent_type,
                "refined_query": request.message,
                "keywords": [],
            },
            assistant_content=facts,
            assistant_meta={
                "recommendations": self._cards_meta(cards),
                "agent_trace": decision.trace,
            },
        )
        return ChatResponseDto(
            chat_id=chat_id,
            reply=facts,
            refined_query=request.message,
            keywords=[],
            intent_type=intent_type,
            search_filters={},
            recommendations=cards,
            conversation_id=conversation_id,
        )

    async def _verify_agent_title(self, title: str | None) -> MovaSearchItemSchema | None:
        """카탈로그 정확 일치만 확정(오케스트레이터 `_verify_title`과 같은 기준)."""
        if not title:
            return None
        items = await self._repo.search_movies_by_title([title], 5)
        wanted = MovieTitle(title)
        exact = [i for i in items if wanted.equals(i.title)]
        return exact[0] if exact else None

    async def _dispatch_slots(
        self, request: MovaChatRequest, trace_id: str, slots: VerifiedSlots
    ) -> ChatResponseDto:
        """검증된 슬롯 → 트랙 실행. 트랙은 이해를 다시 하지 않고 실행만 한다."""
        await self._maybe_record_eval_positive(request, trace_id)
        title = slots.movie.title if slots.movie else slots.title_text
        if slots.intent == "booking" and self._booking is not None:
            result = await self._booking.assist_slots(
                message=request.message,
                title_text=slots.title_text,
                verified_title=slots.movie.title if slots.movie else None,
                region=slots.region,
                trace_id=trace_id,
                history=request.history_dicts(),
            )
            if request.user_id and result.resolved_movie_id and not slots.followup:
                await self._repo.record_user_action(
                    request.user_id, result.resolved_movie_id, "booking_intent"
                )
            return await self._finish_booking(request, trace_id, result, [title] if title else [])
        if slots.intent == "evaluate" and self._evaluation is not None:
            return await self._reply_evaluation(request, trace_id, [title] if title else [])
        if slots.intent == "general":
            return await self._reply_general(request, trace_id)
        return await self._reply_recommend(request, trace_id)

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
            reply=result.reply,
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
        return await self._finish_booking(request, trace_id, result, entities)

    async def _finish_booking(
        self, request: MovaChatRequest, trace_id: str, result: BookingResult, entities: list[str]
    ) -> ChatResponseDto:
        """booking 결과 저장·응답 조립 — 기존 경로와 오케스트레이터 경로가 공유."""
        chat_id = await self._repo.save_chat(
            user_id=request.user_id,
            assistant_id=None,
            raw_message=request.message,
            refined_query=request.message,
            keywords=entities,
            intent_type="booking",
            search_filters={},
            reply=result.reply,
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
        # 지금 상영작 근거(주간 박스오피스) — "인턴 언제 해?"에 2015년작 얘기를 하지 않게
        # (2026-09-27 사용자 지적: 상영 중인 건 2026년작). booking 서비스가 KOFIC을 1시간 캐시로 든다.
        showing = await self._showing_titles_for_general()
        if showing:
            question = f"{question}\n\n[지금 상영 중(주간 박스오피스)]\n{' / '.join(showing)}"
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
            reply=reply_text,
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

    async def _showing_titles_for_general(self) -> list[str]:
        if self._booking is None:
            return []
        try:
            titles = await self._booking.showing_titles()
        except Exception as e:  # 근거는 보조 정보 — 실패해도 잡담 답변은 나가야 한다
            logger.warning("[ChatInteractor] 상영작 근거 조회 실패 — %s", e)
            return []
        return [t for t in titles if isinstance(t, str)] if isinstance(titles, list) else []

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

    async def _watched_slugs(self, request: MovaChatRequest) -> set[str]:
        """사용자가 봤다고 표시한 영화 id 집합. 비로그인이면 빈 집합, 조회 실패도 빈 집합."""
        if not request.user_id:
            return set()
        try:
            ids = await self._repo.get_watched_movie_ids(request.user_id)
            return {str(i) for i in ids}
        except Exception:
            return set()

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
