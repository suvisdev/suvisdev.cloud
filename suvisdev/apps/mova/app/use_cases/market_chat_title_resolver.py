"""evaluate/booking 트랙 공용 — 발화에서 작품을 확정한다.

잘못 짚은 영화를 평가·예매 안내하는 것이 최악의 실패 모드라, 정확 일치가
없고 후보가 여럿이면 ambiguous로 되묻게 한다(설계서 §4-1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort
from mova.domain.value_objects.movie_title import normalize_title

# 발화 꼬리에 붙는 트랙 어휘 — 제목 후보를 만들 때 떼어낸다.
# ("호프 어때??" → "호프", "호프 예매하고 싶어" → "호프")
_TRAILING_PATTERN = re.compile(
    r"[\s]*(어때|어떄|볼만해|볼만한가|재밌어|재미있어|평가|평점|리뷰"
    r"|예매|예약|표|티켓|상영관|상영|영화관|어디서|보고\s*싶|하고\s*싶|싶어|싶은데"
    r"|하고|할래|할까"
    r"|해줘|알려줘|좀|영화)+[\s?!.~]*$"
)
_CANDIDATE_LIMIT = 5

# 한국어 조사·어미 — 발화에서 제목을 분리할 때 쓴다.
# "더문은" → "더문", "인셉션이" → "인셉션"
_PARTICLES = re.compile(
    r"(에서의|에서|한테서|한테|으로|이랑|에게|처럼|까지|부터|마저|조차"
    r"|는|은|이|가|을|를|도|의|에|와|과|랑|로)$"
)


@dataclass(frozen=True)
class TitleResolution:
    status: str  # "ok" | "not_found" | "ambiguous"
    item: MovaSearchItemSchema | None
    candidates: list[MovaSearchItemSchema]


def _strip_particle(word: str) -> str:
    return _PARTICLES.sub("", word)


# 앞 어절 후보에서 제외할 일반어 — "지금 예매…"의 '지금'이 제목이 되면 안 된다.
_LEADING_STOPWORDS = frozenset(
    {
        "지금",
        "오늘",
        "내일",
        "이번",
        "당장",
        "바로",
        "근처",
        "우리집",
        "여기",
        "거기",
        "그",
        "이",
        "저",
        "영화",
    }
)


def _leading_candidates(message: str) -> list[str]:
    """문장 앞 1~2어절(원형 그대로). "파과 예매할 수 있게 시간봐줘 그럼"처럼 꼬리 규칙이
    못 떼는 자유 문장에서 제목이 맨 앞에 오는 관례를 이용한다. 조사는 여기서 떼지 않는다 —
    "파과"의 '과'를 조사로 보고 '파'를 만든 것이 2026-09-27 스파이더맨 오매칭의 원인이다."""
    words = [w for w in message.strip().split() if w]
    out: list[str] = []
    if words and words[0] not in _LEADING_STOPWORDS and len(words[0]) >= 2:
        out.append(words[0])
        if (
            len(words) >= 2
            and words[1] not in _LEADING_STOPWORDS
            and not _TRAILING_PATTERN.fullmatch(words[1])
        ):
            out.append(f"{words[0]} {words[1]}")
    return out


def _word_candidates(message: str) -> list[str]:
    """문장의 어절(조사 제거, 2자 이상, 불용어·꼬리 어휘 제외) — 정확 일치 전용."""
    out: list[str] = []
    for w in message.strip().rstrip("?!.~ ").split():
        stem = _strip_particle(w)
        for cand in (w, stem):
            if (
                len(cand) >= 2
                and cand not in _LEADING_STOPWORDS
                and not _TRAILING_PATTERN.fullmatch(cand)
                and cand not in out
            ):
                out.append(cand)
    return out[:8]


def _title_terms(message: str, entities: list[str]) -> list[str]:
    """분류기 entities(제목이 첫 번째 관례) 우선, 발화에서 꼬리 어휘를 뗀 후보 보강.
    1자 엔티티는 버린다 — '파'가 부분일치로 스파이더맨·임파서블을 끌어온다."""
    terms = [e.strip() for e in entities if len(e.strip()) >= 2]
    stripped = message.strip().rstrip("?!.~ ")
    prev = None
    while prev != stripped:  # "예매하고 싶어"처럼 어휘가 겹쳐 붙은 꼬리를 반복 제거
        prev = stripped
        stripped = _TRAILING_PATTERN.sub("", stripped).strip()
    if stripped and stripped not in terms:
        terms.append(stripped)
    for cand in _leading_candidates(message):
        if cand not in terms:
            terms.append(cand)

    # 조사 분리 — "더문은 쩸 쓰나"에서 첫 어절 "더문은" → "더문".
    # 1자 어간은 버린다: "파과"→"파"가 부분일치로 무관 제목을 끌어왔다(2026-09-27).
    extra: list[str] = []
    for t in terms:
        words = t.split()
        if words:
            stem = _strip_particle(words[0])
            if len(stem) >= 2 and stem != words[0] and stem not in terms:
                extra.append(stem)
    terms.extend(extra)
    return terms[:6]


async def resolve_movie_title(
    repository: ChatRepositoryPort, *, message: str, entities: list[str]
) -> TitleResolution:
    terms = _title_terms(message, entities)
    if not terms:
        return TitleResolution(status="not_found", item=None, candidates=[])

    items = await repository.search_movies_by_title(terms, _CANDIDATE_LIMIT)
    if not items:
        # 어절 정확 일치 — "군자에서 인턴 오늘 몇 시에 볼 수 있어?"처럼 제목이 문장 중간에
        # 있으면 앞 어절 후보('군자')가 퍼지로 군체·구원자·감자를 끌어온다(2026-09-27 라이브).
        # 퍼지 전에 각 어절(조사 뗀 것)이 제목과 정확히 같은지 본다.
        words = _word_candidates(message)
        if words:
            by_word = await repository.search_movies_by_title(words, _CANDIDATE_LIMIT)
            word_norms = {normalize_title(w) for w in words}
            exact_words = [i for i in by_word if normalize_title(i.title) in word_norms]
            if exact_words:
                return TitleResolution(status="ok", item=exact_words[0], candidates=by_word)
        # 퍼지 폴백 — 자모 편집거리로 가장 유사한 제목을 찾는다.
        items = await repository.fuzzy_search_movies_by_title(terms, _CANDIDATE_LIMIT)
        if not items:
            return TitleResolution(status="not_found", item=None, candidates=[])
        if len(items) == 1:
            return TitleResolution(status="ok", item=items[0], candidates=items)
        return TitleResolution(status="ambiguous", item=None, candidates=items[:3])

    # 정확 일치(공백·대소문자 무시)가 있으면 그중 첫 항목(평점·최신 우선 정렬).
    normalized_terms = {normalize_title(t) for t in terms}
    exact = [i for i in items if normalize_title(i.title) in normalized_terms]
    if exact:
        return TitleResolution(status="ok", item=exact[0], candidates=items)
    if len(items) == 1:
        return TitleResolution(status="ok", item=items[0], candidates=items)
    return TitleResolution(status="ambiguous", item=None, candidates=items[:3])
