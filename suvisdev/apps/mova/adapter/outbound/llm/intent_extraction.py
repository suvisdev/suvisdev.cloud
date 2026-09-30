import re
from datetime import UTC, datetime
from typing import Any

from mova.domain.value_objects.companion_expansion import expand_companion_genres

MAX_CHAT_KEYWORDS = 24

INTENT_FILTER_AND = "filter_and"
INTENT_SIMILAR_PERSON = "similar_person"
INTENT_MOOD = "mood"

# 문두 담화어는 반드시 공백이 뒤따를 때만 뗀다(\s+) — \s*였을 때 "좀비 영화"의
# "좀"이 잘려 "비 영화"(rain)로 RAG·태그 검색이 전부 오염됐다(2026-09-02 실측,
# 9/1 "좀비 recs=0" 사고의 진짜 뿌리).
_FILLER = re.compile(
    r"^(오늘|지금|좀|그냥|please|plz)\s+|[\s,]*(보여줘|보여 줘|추천해줘|추천 해줘|알려줘|찾아줘|해줘|해 줘|틀어줘|틀어 줘|있어|있나|할래|싶어|주세요|줘)\s*$",
    re.IGNORECASE,
)

_STOPWORDS = frozenset(
    {
        "영화",
        "시리즈",
        "추천",
        "보여",
        "보여줘",
        "해줘",
        "해",
        "주세요",
        "관련",
        "나오는",
        "출연",
        "장르",
        "하나",
        "좀",
        "그냥",
        "오늘",
        "지금",
        "please",
        "movie",
        "film",
        "배우",
        "비슷한",
        "비슷",
        "같은",
    },
)

_GENRE_PHRASES: tuple[str, ...] = (
    "스릴러",
    "로맨스",
    "로맨틱",
    "코미디",
    "액션",
    "드라마",
    "공포",
    "호러",
    "멜로",
    "sf",
    "SF",
    "판타지",
    "다큐",
    "애니",
    "애니메이션",
    "범죄",
    "전쟁",
    "뮤지컬",
    "가족",
    "느와르",
    "전기",
)

_GENRE_SET = frozenset(g.lower() for g in _GENRE_PHRASES)

# 사용자 표현 → TMDB origin_country(ISO 3166-1 alpha-2). `movies.origin_country`가
# 이 코드 배열이라 후보 쿼리에서 그대로 대조한다.
_COUNTRY_ALIASES: dict[str, str] = {
    "한국": "KR",
    "국내": "KR",
    "우리나라": "KR",
    "korea": "KR",
    "korean": "KR",
    "미국": "US",
    "헐리우드": "US",
    "할리우드": "US",
    "usa": "US",
    "america": "US",
    "영국": "GB",
    "british": "GB",
    "uk": "GB",
    "일본": "JP",
    "japan": "JP",
    "중국": "CN",
    "china": "CN",
    "대만": "TW",
    "홍콩": "HK",
    "프랑스": "FR",
    "france": "FR",
    "독일": "DE",
    "이탈리아": "IT",
    "스페인": "ES",
    "인도": "IN",
    "캐나다": "CA",
    "호주": "AU",
    "태국": "TH",
}

_DECADE_RE = re.compile(r"(\d{2,4})\s*년대")
_YEAR_RE = re.compile(r"(19\d{2}|20\d{2})\s*년(?!대)")

# "클래식 명작 처음 보는 사람용" 실사고(2026-08-28): 시대 어휘가 연도 조건으로
# 해석되지 않아 하드 필터 0개 → 인기작 폴백(최근 15년 우선)이 클래식 요청에
# 최신작만 돌려줬다. 명시적 연대·연도가 없을 때만 상한 1999로 근사한다.
_ERA_WORDS = ("클래식", "고전", "옛날")
_ERA_YEAR_MAX = 1999

# "최신영화 알려줘" 실사고(2026-09-02): 클래식과 대칭으로 최신 어휘도 연도
# 조건으로 해석한다 — 최신·신작은 올해-1(진짜 신작 기대), 최근은 올해-5.
_RECENT_STRICT_WORDS = ("최신", "신작")
_RECENT_STRICT_SPAN = 1
_RECENT_LOOSE_WORDS = ("최근",)
_RECENT_LOOSE_SPAN = 5


def _guess_countries(text: str) -> list[str]:
    hay = text.lower()
    out: list[str] = []
    for alias, code in _COUNTRY_ALIASES.items():
        if alias in hay and code not in out:
            out.append(code)
    return out


def _guess_year_range(text: str) -> tuple[int | None, int | None]:
    """ "2020년대"→(2020,2029), "90년대"→(1990,1999), "2015년"→(2015,2015)."""
    m = _DECADE_RE.search(text)
    if m:
        raw = int(m.group(1))
        # "90년대"처럼 두 자리면 1900년대로 본다(2000년대 이후는 네 자리로 쓴다).
        start = raw if raw >= 1000 else 1900 + raw
        return start, start + 9
    m = _YEAR_RE.search(text)
    if m:
        year = int(m.group(1))
        return year, year
    if any(word in text for word in _ERA_WORDS):
        return None, _ERA_YEAR_MAX
    if any(word in text for word in _RECENT_STRICT_WORDS):
        return datetime.now(UTC).year - _RECENT_STRICT_SPAN, None
    if any(word in text for word in _RECENT_LOOSE_WORDS):
        return datetime.now(UTC).year - _RECENT_LOOSE_SPAN, None
    return None, None


def merge_keyword_lists(*lists: list[str] | None, limit: int = MAX_CHAT_KEYWORDS) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for lst in lists:
        for raw in lst or []:
            k = str(raw).strip()
            if not k:
                continue
            key = k.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(k)
            if len(out) >= limit:
                return out
    return out


def _empty_filters() -> dict[str, Any]:
    return {
        "must": {"actors": [], "genres": [], "keywords": [], "countries": []},
        "similar_to": {"actors": []},
        "match_mode": "any",
        "year_min": None,
        "year_max": None,
    }


def _coerce_str_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _guess_actors(text: str) -> list[str]:
    found: list[str] = []
    for m in re.finditer(
        r"([\w가-힣]{2,10})\s*(?:배우|출연|관련|이랑|와|과|이\s*나오는|가\s*나오는)",
        text,
    ):
        name = m.group(1).strip()
        if name.lower() in _STOPWORDS or name.lower() in _GENRE_SET:
            continue
        found.append(name)
    return merge_keyword_lists(found, limit=8)


def _guess_genres(text: str, keywords: list[str]) -> list[str]:
    hay = f"{text} {' '.join(keywords)}".lower()
    out: list[str] = []
    for phrase in _GENRE_PHRASES:
        if phrase.lower() in hay:
            out.append(phrase)
    return merge_keyword_lists(out, limit=8)


def build_search_filters(
    message: str,
    keywords: list[str],
    parsed: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """의도 분류 + AND(must) / similar_to 구조."""
    parsed = parsed or {}
    cleaned = _FILLER.sub("", message).strip()

    _must_val = parsed.get("must")
    must_raw: dict[str, Any] = _must_val if isinstance(_must_val, dict) else {}
    _sim_val = parsed.get("similar_to")
    similar_raw: dict[str, Any] = _sim_val if isinstance(_sim_val, dict) else {}

    must_actors = merge_keyword_lists(
        _coerce_str_list(must_raw.get("actors")),
        _guess_actors(cleaned),
        limit=8,
    )
    must_genres = merge_keyword_lists(
        _coerce_str_list(must_raw.get("genres")),
        _guess_genres(cleaned, keywords),
        expand_companion_genres(cleaned),  # 동행 맥락("여자친구랑 볼 영화") → 장르 선호
        limit=8,
    )
    must_keywords = merge_keyword_lists(
        _coerce_str_list(must_raw.get("keywords")),
        limit=8,
    )
    similar_actors = merge_keyword_lists(
        _coerce_str_list(similar_raw.get("actors")),
        limit=8,
    )

    intent_raw = str(parsed.get("intent_type", "")).strip().lower()
    has_similar_phrase = "비슷" in cleaned or "같은 느낌" in cleaned or "유사" in cleaned

    if intent_raw in {INTENT_FILTER_AND, INTENT_SIMILAR_PERSON, INTENT_MOOD}:
        intent_type = intent_raw
    elif has_similar_phrase or similar_actors:
        intent_type = INTENT_SIMILAR_PERSON
        if not similar_actors:
            similar_actors = merge_keyword_lists(must_actors, _guess_actors(cleaned), limit=8)
    elif must_actors and must_genres:
        intent_type = INTENT_FILTER_AND
    elif len(must_actors) + len(must_genres) + len(must_keywords) >= 2:
        intent_type = INTENT_FILTER_AND
    else:
        intent_type = INTENT_MOOD

    if intent_type == INTENT_SIMILAR_PERSON and not similar_actors:
        similar_actors = merge_keyword_lists(must_actors, _guess_actors(cleaned), limit=8)

    # 국가·연도는 후보를 좁히는 하드 조건이라 LLM 응답이 없어도 원문에서 직접 뽑는다
    # (Gemini 추출이 실패해도 "2020년대 한국 액션"이 동작해야 한다).
    must_countries = merge_keyword_lists(
        [
            c
            for c in _coerce_str_list(must_raw.get("countries"))
            if c.upper() in set(_COUNTRY_ALIASES.values())
        ],
        _guess_countries(cleaned),
        limit=4,
    )
    year_min, year_max = _guess_year_range(cleaned)

    match_mode = "all" if intent_type == INTENT_FILTER_AND else "any"
    search_filters: dict[str, Any] = {
        "must": {
            "actors": must_actors,
            "genres": must_genres,
            "keywords": must_keywords,
            "countries": must_countries,
        },
        "similar_to": {"actors": similar_actors},
        "match_mode": match_mode,
        "year_min": year_min,
        "year_max": year_max,
    }
    return intent_type, search_filters


def normalize_keywords(
    message: str,
    refined_query: str,
    extracted: list[str] | None,
    *,
    search_filters: dict[str, Any] | None = None,
    limit: int = MAX_CHAT_KEYWORDS,
) -> list[str]:
    parts: list[str] = list(extracted or [])
    must = (search_filters or {}).get("must") or {}
    similar = (search_filters or {}).get("similar_to") or {}
    parts.extend(_coerce_str_list(must.get("actors")))
    parts.extend(_coerce_str_list(must.get("genres")))
    parts.extend(_coerce_str_list(must.get("keywords")))
    parts.extend(_coerce_str_list(similar.get("actors")))

    cleaned = _FILLER.sub("", message).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    for phrase in _GENRE_PHRASES:
        if phrase.lower() in cleaned.lower():
            parts.append(phrase)

    for m in re.finditer(r"비슷한\s*[\w가-힣]+", cleaned):
        parts.append(m.group(0).strip())
    for m in re.finditer(r"[\w가-힣]{2,}(?:\s+배우|\s*출연)", cleaned):
        parts.append(re.sub(r"\s*(배우|출연)\s*$", "", m.group(0)).strip())

    for token in re.split(r"[\s,·/]+", cleaned):
        t = token.strip()
        if len(t) < 2 or t.lower() in _STOPWORDS:
            continue
        parts.append(t)

    if refined_query.strip():
        rq = refined_query.strip()
        parts.append(rq)
        for token in re.split(r"[\s,·/]+", rq):
            t = token.strip()
            if len(t) >= 2 and t.lower() not in _STOPWORDS:
                parts.append(t)

    return merge_keyword_lists(parts, limit=limit)


class IntentExtractionService:
    def extract(self, message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
        """현재 턴(text)만 결정론적으로 추출한다.

        Gemini 보조 추출은 2026-09-11 제거 — 08-19 멀티턴 오염 수정 2건
        (f59f1d4·5c9c24c)이 이전 턴 유입을 막으려고 Gemini 산출물(refined_query·
        keywords·must·similar_to)을 전부 결정론 결과로 덮으면서, 호출은 남았는데
        결과는 어디에도 쓰이지 않는 상태였다(평시 0.9s·쿼터 압박 시 SDK 재시도로
        3.7~5s 지연 + 질의당 쿼터 1건 낭비). history는 포트 시그니처 유지용으로
        받되 사용하지 않는다 — 멀티턴 맥락은 interactor의 past_intents(프롬프트
        주입) 경로가 담당한다.
        """
        _ = history
        text = message.strip()
        if not text:
            return {
                "refined_query": "",
                "keywords": [],
                "intent_type": INTENT_MOOD,
                "search_filters": _empty_filters(),
            }

        deterministic = self._fallback_raw(text)
        refined = str(deterministic.get("refined_query", "")).strip()[:255]
        det_kw = deterministic.get("keywords") or []
        raw_kw = det_kw if isinstance(det_kw, list) else []

        intent_type, search_filters = build_search_filters(text, raw_kw, deterministic)
        keywords = normalize_keywords(
            text,
            refined,
            raw_kw,
            search_filters=search_filters,
        )

        if not refined and keywords:
            refined = " ".join(keywords[:4])[:40]
        if not refined:
            refined = text[:255]

        return {
            "refined_query": refined,
            "keywords": keywords,
            "intent_type": intent_type,
            "search_filters": search_filters,
        }

    def _fallback_raw(self, message: str) -> dict[str, Any]:
        cleaned = _FILLER.sub("", message).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        refined = cleaned[:40] if cleaned else message[:40]
        # 불용어를 여기서 빼야 한다 — normalize_keywords는 이 목록(extracted)을 거르지 않고
        # 합친다. "영화"가 남으면 태그 검색 ILIKE가 "TV 영화" 10편을 실매칭으로 물어와
        # 분위기 질의가 같은 2025~26년 TV 영화로 채워졌다(2026-09-28 repeated_titles 4건 전부).
        tokens = [
            t for t in re.split(r"[\s,·/]+", cleaned) if len(t) >= 2 and t.lower() not in _STOPWORDS
        ]
        intent_type, search_filters = build_search_filters(message, tokens, {})
        keywords = normalize_keywords(message, refined, tokens, search_filters=search_filters)
        return {
            "refined_query": refined,
            "keywords": keywords,
            "intent_type": intent_type,
            "must": search_filters.get("must"),
            "similar_to": search_filters.get("similar_to"),
            "search_filters": search_filters,
        }
