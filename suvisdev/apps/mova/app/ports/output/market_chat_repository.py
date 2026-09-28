"""채팅 출력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

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
    async def get_catalog_items(self, movie_ids: list[int]) -> list[MovaSearchItemSchema]:
        """RAG 시맨틱 히트의 movie_id를 카탈로그 아이템(연도·장르·줄거리·투표 수)으로 채운다.

        hub 히트는 제목뿐이라 프롬프트에 "연도 미상"·줄거리 없음으로 실려 LLM이 제목만 보고
        골랐고(2026-09-28 "비 오는 날"→"비와 당신의 이야기"), 품질 하한도 판정할 수 없었다.
        입력 순서를 유지하며, DB에 없는 id는 빠진다.
        """

    @abstractmethod
    async def filter_movie_ids_by_year(
        self,
        movie_ids: list[int],
        year_min: int | None,
        year_max: int | None,
    ) -> set[int]:
        """주어진 영화 id 중 연도 하드 조건을 만족하는 id만 돌려준다.

        RAG 시맨틱 히트는 hub에 연도 메타데이터가 없어 year_min/max를 못
        지키므로(2026-09-03 "클래식 명작" 실사고 — 1999 이하 요청에 2003·2007년
        작이 후보로 유입), 히트의 movie_id를 movies.release_year로 재검증할 때
        쓴다. release_year=0(미상)은 판정 불가라 조건이 있으면 탈락시킨다.
        """

    @abstractmethod
    async def search_movies_by_title(
        self, terms: list[str], limit: int
    ) -> list[MovaSearchItemSchema]:
        """제목 부분일치 후보(평점·최신 우선 정렬) — evaluate/booking 트랙의 작품 확정용."""

    async def fuzzy_search_movies_by_title(
        self, terms: list[str], limit: int
    ) -> list[MovaSearchItemSchema]:
        """자모 분해 편집거리 기반 퍼지 검색 — exact 검색 0건일 때 폴백."""
        return []

    async def find_movie_titled_in_text(self, text: str) -> MovaSearchItemSchema | None:
        """text 안에 제목이 그대로 언급된 카탈로그 영화를 역방향으로 찾는다(가장 긴 제목 우선).

        evaluate 후속 이어받기용 — "어떠냐고"처럼 제목 없는 발화가 왔을 때,
        직전 assistant 메시지(영화를 소개한 문장)에서 작품을 복원한다.
        """
        return None

    @abstractmethod
    async def record_user_action(self, user_id: int, movie_id: int, action_type: str) -> None:
        """user_actions 이벤트 기록 — chat_trend 조건부 신호(booking_intent·eval_positive)."""

    @abstractmethod
    async def get_recent_intents_by_user(self, user_id: int, limit: int) -> list[Any]:
        """사용자 최근 검색 의도 (MovaChat rows)."""

    @abstractmethod
    async def get_watched_movie_ids(self, user_id: int) -> set[str]:
        """사용자가 "봤어요"(user_actions watched)로 표시한 영화 id 집합(문자열, 후보 id와 같은 형식)."""

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
        search_filters: dict[str, Any],
        reply: str | None,
    ) -> int:
        """chat 저장 → chat.id 반환. `reply`는 LLM 응답 본문(학습 자료용)."""

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
