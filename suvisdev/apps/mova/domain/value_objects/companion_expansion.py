"""동행(누구와 보는가) 어휘 → 장르 선호 확장.

"여자친구랑 볼 영화"·"아이랑 볼 만한 영화"처럼 **누구와 함께 보는지**가 장르 선호를 암시한다.
이건 작품 내용 매칭(RAG)이 아니라 "시청 맥락 → 장르" 추론이라, 의도 이해 단계에서 장르로 환원해
`must.genres`에 얹는다(하드 필터 아님 — `normalize_keywords`가 keywords로 합쳐 태그 후보를 그쪽으로
넓히는 합집합 신호). 대중 장르 화이트리스트(`mood_expansion.POPULAR_GENRES`)만 통과한다.

오탐 방지: "아이"·"친구"처럼 짧은 명사는 "아이언맨"·"여자친구"에 부분일치하므로, **동반 조사**
(랑·이랑·와·과·하고)가 붙을 때만 잡는다. "데이트"·"커플"은 그 자체로 동행 맥락이라 조사 없이 잡는다.
"""

from __future__ import annotations

import re

from mova.domain.value_objects.mood_expansion import POPULAR_GENRES

# 동행어 → 암시 장르(대중 장르만). 연인=로맨스·코미디, 아이·가족=애니메이션·모험, 부모=드라마, 친구=코미디·액션.
_COMPANION_GENRES: dict[str, tuple[str, ...]] = {
    "여자친구": ("로맨스", "코미디"),
    "여친": ("로맨스", "코미디"),
    "남자친구": ("로맨스", "코미디"),
    "남친": ("로맨스", "코미디"),
    "애인": ("로맨스", "코미디"),
    "연인": ("로맨스", "코미디"),
    "데이트": ("로맨스", "코미디"),
    "커플": ("로맨스", "코미디"),
    "아이": ("애니메이션", "모험"),
    "애기": ("애니메이션", "모험"),
    "아기": ("애니메이션", "모험"),
    "딸": ("애니메이션", "모험"),
    "아들": ("애니메이션", "모험"),
    "조카": ("애니메이션", "모험"),
    "애들": ("애니메이션", "모험"),
    "가족": ("애니메이션", "모험", "드라마"),
    "온가족": ("애니메이션", "모험", "드라마"),
    "식구": ("애니메이션", "모험", "드라마"),
    "부모님": ("드라마",),
    "엄마": ("드라마",),
    "아빠": ("드라마",),
    "어머니": ("드라마",),
    "아버지": ("드라마",),
    "친구들": ("코미디", "액션"),
    "친구": ("코미디", "액션"),
}

# 동반 조사가 붙는 명사(오탐 방지). "친구들"이 "친구"보다 앞이라 "친구들하고"가 친구들로 잡힌다.
_WITH_PARTICLE = re.compile(
    r"(여자친구|여친|남자친구|남친|애인|연인|아이|애기|아기|딸|아들|조카|애들|"
    r"가족|온가족|식구|부모님|엄마|아빠|어머니|아버지|친구들|친구)\s*(?:랑|이랑|와|과|하고)"
)
# 조사 없이도 동행 맥락이 분명한 표현.
_STANDALONE = re.compile(r"데이트|커플")


def expand_companion_genres(text: str) -> list[str]:
    """text의 동행 표현이 암시하는 대중 장르를 반환(등장 순서 유지, 중복·비화이트리스트 제거)."""
    words = [m.group(1) for m in _WITH_PARTICLE.finditer(text)]
    words += [m.group(0) for m in _STANDALONE.finditer(text)]
    out: list[str] = []
    seen: set[str] = set()
    for word in words:
        for genre in _COMPANION_GENRES.get(word, ()):
            if genre in POPULAR_GENRES and genre not in seen:
                out.append(genre)
                seen.add(genre)
    return out
