"""외부 리뷰 조회 출력 포트 — evaluate 트랙 전용.

왓챠피디아 등 크롤링 소스는 약관·DB권 리스크로 제외 확정(2026-08-28,
`_docs/MOVA_CHAT_INTENT_REDESIGN.md` §8-1). 공식 API(TMDB)만 구현한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ExternalReviewPort(ABC):
    @abstractmethod
    async def fetch_reviews(self, tmdb_id: int, *, limit: int = 3) -> list[str]:
        """TMDB 리뷰 본문 목록(실패·없음이면 빈 리스트 — 평가 흐름은 계속돼야 한다)."""
