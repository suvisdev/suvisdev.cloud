"""evaluate/booking 트랙 공용 — 발화에서 작품을 확정한다.

잘못 짚은 영화를 평가·예매 안내하는 것이 최악의 실패 모드라, 정확 일치가
없고 후보가 여럿이면 ambiguous로 되묻게 한다(설계서 §4-1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.app.ports.output.market_chat_repository import ChatRepositoryPort

# 발화 꼬리에 붙는 트랙 어휘 — 제목 후보를 만들 때 떼어낸다.
# ("호프 어때??" → "호프", "호프 예매하고 싶어" → "호프")
_TRAILING_PATTERN = re.compile(
    r"[\s]*(어때|어떄|볼만해|볼만한가|재밌어|재미있어|평가|평점|리뷰"
    r"|예매|예약|표|티켓|상영관|상영|영화관|어디서|보고\s*싶|하고\s*싶|싶어|싶은데"
    r"|하고|할래|할까"
    r"|해줘|알려줘|좀|영화)+[\s?!.~]*$"
)
_CANDIDATE_LIMIT = 5


@dataclass(frozen=True)
class TitleResolution:
    status: str  # "ok" | "not_found" | "ambiguous"
    item: MovaSearchItemSchema | None
    candidates: list[MovaSearchItemSchema]


def _title_terms(message: str, entities: list[str]) -> list[str]:
    """분류기 entities(제목이 첫 번째 관례) 우선, 발화에서 꼬리 어휘를 뗀 후보 보강."""
    terms = [e.strip() for e in entities if e.strip()]
    stripped = message.strip().rstrip("?!.~ ")
    prev = None
    while prev != stripped:  # "예매하고 싶어"처럼 어휘가 겹쳐 붙은 꼬리를 반복 제거
        prev = stripped
        stripped = _TRAILING_PATTERN.sub("", stripped).strip()
    if stripped and stripped not in terms:
        terms.append(stripped)
    return terms[:4]


def _normalize(title: str) -> str:
    return re.sub(r"\s+", "", title).lower()


async def resolve_movie_title(
    repository: ChatRepositoryPort, *, message: str, entities: list[str]
) -> TitleResolution:
    terms = _title_terms(message, entities)
    if not terms:
        return TitleResolution(status="not_found", item=None, candidates=[])

    items = await repository.search_movies_by_title(terms, _CANDIDATE_LIMIT)
    if not items:
        return TitleResolution(status="not_found", item=None, candidates=[])

    # 정확 일치(공백·대소문자 무시)가 있으면 그중 첫 항목(평점·최신 우선 정렬).
    normalized_terms = {_normalize(t) for t in terms}
    exact = [i for i in items if _normalize(i.title) in normalized_terms]
    if exact:
        return TitleResolution(status="ok", item=exact[0], candidates=items)
    if len(items) == 1:
        return TitleResolution(status="ok", item=items[0], candidates=items)
    return TitleResolution(status="ambiguous", item=None, candidates=items[:3])
