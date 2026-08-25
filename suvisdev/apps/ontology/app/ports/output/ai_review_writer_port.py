"""AI 리뷰 생성 파이프라인의 DB 접근 포트 — movie_id 매칭 + 리뷰 쓰기."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AiReviewWriterPort(ABC):
    @abstractmethod
    async def find_movie_id_by_title(self, title: str) -> int | None:
        """movies 테이블에서 title로 movie_id를 찾는다. 없으면 None."""

    @abstractmethod
    async def ensure_ai_reviewer_user(self) -> int:
        """ai_reviewer 시스템 계정의 user_id를 반환한다. 없으면 생성."""

    @abstractmethod
    async def has_ai_review(self, user_id: int, movie_id: int) -> bool:
        """이미 AI 리뷰가 존재하는지 확인한다."""

    @abstractmethod
    async def save_review(
        self, *, user_id: int, movie_id: int, rating: float, body: str
    ) -> int:
        """리뷰를 저장하고 review_id를 반환한다."""
