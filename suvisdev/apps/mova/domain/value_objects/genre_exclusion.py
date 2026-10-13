"""발화의 "싫은 장르" → 추천 후보에서 뺄 카탈로그 장르(2026-10-07).

배경: "공포는 싫고 긴장감 있는 영화"에 컨저링 3·콰이어트 플레이스 2를 추천했다(운영 실측). 의도 추출도
RAG 검색도 부정을 모른다 — 오히려 "공포"라는 낱말 때문에 공포물이 더 가까이 잡힌다. 부정 표현은
낱말 몇 개로 정해져 있어 코드로 확실히 판정되므로 모델에 맡기지 않는다.

- 장르 + (은/는/물은/영화는…) + 싫/말고/빼고/제외/별로/말구/아니고 → 그 장르를 뺀다.
- 검색어에서도 그 구절을 지운다("공포는 싫고 긴장감 있는 영화" → "긴장감 있는 영화").
라벨은 DB tags(tag_kind=genre)의 실제 값이다.
"""

from __future__ import annotations

import re

# 사용자 표현 → DB 장르 라벨
_GENRE_WORDS: dict[str, str] = {
    "공포": "공포",
    "호러": "공포",
    "무서운": "공포",
    "로맨스": "로맨스",
    "멜로": "로맨스",
    "연애": "로맨스",
    "액션": "액션",
    "코미디": "코미디",
    "애니메이션": "애니메이션",
    "애니": "애니메이션",
    "만화": "애니메이션",
    "SF": "SF",
    "공상과학": "SF",
    "스릴러": "스릴러",
    "드라마": "드라마",
    "판타지": "판타지",
    "범죄": "범죄",
    "전쟁": "전쟁",
    "다큐": "다큐멘터리",
    "다큐멘터리": "다큐멘터리",
    "뮤지컬": "뮤지컬",
    "음악": "음악",
    "가족": "가족",
    "미스터리": "미스터리",
    "역사": "역사",
    "모험": "모험",
    "서부": "서부",
}
# 긴 낱말부터 — "애니메이션"이 "애니"보다 먼저 잡히게
_WORDS = "|".join(sorted(map(re.escape, _GENRE_WORDS), key=len, reverse=True))
_NEGATED = re.compile(
    rf"({_WORDS})\s*(?:물|영화|장르|류|쪽|거|것|같은\s*거)?\s*(?:은|는|이|가|도)?\s*"
    r"(?:싫(?:고|어|은데|으니|으면)?|말고|말구|빼고|제외(?:하고)?|별로(?:고|라서)?|아니고|안\s*(?:좋|땡|당기))"
    r"[,\s]*",
    re.IGNORECASE,
)


def excluded_genres(message: str) -> tuple[frozenset[str], str]:
    """(뺄 장르 라벨들, 부정 구절을 지운 검색어). 부정이 없으면 (빈 집합, 원문)."""
    found = {
        _GENRE_WORDS.get(m.group(1)) or _GENRE_WORDS.get(m.group(1).upper(), "")
        for m in _NEGATED.finditer(message or "")
    }
    found.discard("")
    if not found:
        return frozenset(), message
    cleaned = _NEGATED.sub(" ", message).strip()
    return frozenset(found), re.sub(r"\s+", " ", cleaned) or message


def has_excluded_genre(genres: str, excluded: frozenset[str]) -> bool:
    """카탈로그 항목의 장르 문자열("공포, 스릴러")에 뺄 장르가 있는가. 장르를 모르면(빈 값) 남긴다."""
    if not excluded or not genres:
        return False
    return any(g.strip() in excluded for g in genres.split(","))
