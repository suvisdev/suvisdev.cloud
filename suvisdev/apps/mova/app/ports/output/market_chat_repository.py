"""채팅 출력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from mova.adapter.inbound.api.schemas.market_chat_schema import (
    MovaChatRecommendationSchema,
)
from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema


class ChatRepositoryPort(ABC):
    @abstractmethod
    async def search_tag_catalog(
        self,
        keywords: list[str],
        limit: int,
        *,
        actor_names: list[str] | None = None,
        countries: list[str] | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        title_terms: list[str] | None = None,
    ) -> list[MovaSearchItemSchema]:
        """keywords(tags.label ILIKE)·actor_names(출연진/감독 이름) → 영화 후보.

        둘 다 있으면 교집합(actor_names 조건까지 동시에 만족)을 우선 시도하고,
        교집합이 0건이면 합집합으로 완화한다. 그마저 0건이면(아무 조건도 안
        맞으면) 평점순 인기작으로 폴백 — 빈 후보를 주면 LLM이 카탈로그에 없는
        movie_id를 스스로 지어내고 나중에 전부 드롭돼 "답변은 자신있는데
        카드 0개"가 되는 문제를 완화한다.

        `countries`(ISO 3166-1 alpha-2)·`year_min`/`year_max`는 **완화되지 않는
        하드 조건**이다 — 태그/배우 매칭 결과와 인기작 폴백 **양쪽 모두**에
        적용한다. 폴백에까지 걸어야 "2020년대 한국 액션"에 헐리우드 인기작을
        후보로 주고 LLM이 전부 거절해 0카드가 되는 일을 막는다.
        """

    @abstractmethod
    async def search_movies_by_title(
        self, terms: list[str], limit: int
    ) -> list[MovaSearchItemSchema]:
        """제목 부분일치 후보(평점·최신 우선 정렬) — evaluate/booking 트랙의 작품 확정용."""

    @abstractmethod
    async def record_user_action(self, user_id: int, movie_id: int, action_type: str) -> None:
        """user_actions 이벤트 기록 — chat_trend 조건부 신호(booking_intent·eval_positive)."""

    @abstractmethod
    async def get_recent_intents_by_user(self, user_id: int, limit: int) -> list:
        """사용자 최근 검색 의도 (MovaChat rows)."""

    @abstractmethod
    async def save_chat(
        self,
        *,
        user_id: int | None,
        assistant_id: int | None,
        raw_message: str,
        refined_query: str,
        keywords: list[str],
        intent_type: str,
        search_filters: dict,
    ) -> int:
        """chat 저장 → chat.id 반환."""

    @abstractmethod
    async def save_picks(
        self,
        *,
        chat_id: int,
        user_id: int | None,
        recommendations: list[MovaChatRecommendationSchema],
        batch_at: datetime,
    ) -> None:
        """picks 저장 (slug → movie_id 조회 포함)."""
