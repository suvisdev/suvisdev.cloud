"""리뷰 출력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mova.app.dtos.market_reviews_dto import (
    MovieRatingSummaryDto,
    ReviewActivityDto,
    ReviewCommentDto,
    ReviewDto,
    ReviewWithUserDto,
)


class ReviewsRepositoryPort(ABC):
    @abstractmethod
    async def add_activity(
        self, user_id: int, movie_id: int, action_type: str
    ) -> ReviewActivityDto:
        """이벤트(favorite/watched/click/not_interested) 기록."""

    @abstractmethod
    async def has_watched(self, user_id: int, movie_id: int) -> bool:
        """user_actions에 action_type=watched 기록이 있는지(리뷰 작성 게이트용)."""

    @abstractmethod
    async def add_review(
        self, user_id: int, movie_id: int, rating: float | None, body: str | None
    ) -> ReviewDto:
        """별점·감상평 리뷰 저장 (action_type=review). 별점만/본문만/둘 다 허용."""

    @abstractmethod
    async def find_by_user_and_movie(self, user_id: int, movie_id: int) -> ReviewDto | None:
        """user_id+movie_id 기존 리뷰 조회 (중복 INSERT 방지용)."""

    @abstractmethod
    async def get_by_id(self, review_id: int) -> ReviewDto | None:
        """리뷰 단건 조회 (소유권 검증용)."""

    @abstractmethod
    async def get_by_movie(self, movie_id: int, limit: int, offset: int) -> list[ReviewWithUserDto]:
        """영화별 리뷰 목록 (user join)."""

    @abstractmethod
    async def update_review(
        self, review_id: int, rating: float | None, body: str | None
    ) -> ReviewDto | None:
        """리뷰 수정. body가 변경되면 spoiler_spans는 자동으로 []로 초기화된다
        (백그라운드 재감지 전까지 이전 스팬을 그대로 두면 텍스트와 안 맞을 수 있어서)."""

    @abstractmethod
    async def update_spoiler_spans(self, review_id: int, spans: list[dict[str, Any]]) -> None:
        """AI 감지 결과 반영(백그라운드 태스크에서 호출). 없으면 조용히 스킵."""

    @abstractmethod
    async def get_rating_summary(self, movie_id: int) -> MovieRatingSummaryDto:
        """영화 평균 별점·리뷰 수."""

    @abstractmethod
    async def delete_review(self, review_id: int) -> bool:
        """리뷰 삭제. 존재하지 않으면 False."""

    @abstractmethod
    async def add_comment(self, review_id: int, user_id: int, body: str) -> ReviewCommentDto:
        """리뷰 댓글 작성."""

    @abstractmethod
    async def get_comments_by_review(self, review_id: int) -> list[ReviewCommentDto]:
        """리뷰 댓글 목록(작성순)."""

    @abstractmethod
    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        """본인 댓글 삭제 — WHERE id AND user_id로 소유권을 쿼리에 함께 건다.
        없는 것과 남의 것을 구분해 알려주지 않는다(존재 캐내기 방지)."""

    @abstractmethod
    async def get_body_for_embedding(self, review_id: int) -> str | None:
        """임베딩 대상 body 조회. 리뷰가 없거나 body가 비면 None(→ 스킵)."""

    @abstractmethod
    async def list_missing_embedding(self, limit: int | None) -> list[tuple[int, str]]:
        """embedding IS NULL AND body IS NOT NULL인 (id, body) 순회 — CLI 백필용."""

    @abstractmethod
    async def update_embedding(self, review_id: int, embedding: list[float]) -> None:
        """리뷰 임베딩 저장. 존재하지 않으면 조용히 스킵."""

    @abstractmethod
    async def list_embedded_reviews_by_user(
        self, user_id: int
    ) -> list[tuple[int, float, list[float], str | None, float | None]]:
        """embedding·rating이 모두 있는 유저 리뷰 — 취향 벡터 계산용.

        반환: [(review_id, rating, embedding, sentiment_label, sentiment_score), ...].
        """

    @abstractmethod
    async def list_missing_sentiment(self, limit: int | None) -> list[tuple[int, str]]:
        """sentiment_label IS NULL AND body IS NOT NULL인 (id, body) — 감정분석 배치용."""

    @abstractmethod
    async def update_sentiment(
        self, review_id: int, label: str, score: float
    ) -> None:
        """Echo 감정분석 결과 저장. 존재하지 않으면 조용히 스킵."""

    @abstractmethod
    async def update_rating_if_null(self, review_id: int, rating: float) -> bool:
        """rating이 NULL인 리뷰에만 별점 설정. 반환: 실제 갱신 여부."""

    @abstractmethod
    async def get_sentiment_summary(
        self, movie_id: int
    ) -> tuple[int, int, int]:
        """영화별 감정 집계 (긍정 수, 부정 수, 전체 수)."""

    @abstractmethod
    async def toggle_vote(self, review_id: int, user_id: int) -> tuple[bool, int]:
        """투표 토글. 반환: (현재 투표 상태, 총 투표 수)."""

    @abstractmethod
    async def get_vote_count(self, review_id: int) -> int:
        """리뷰의 투표 수."""

    @abstractmethod
    async def has_voted(self, review_id: int, user_id: int) -> bool:
        """사용자가 해당 리뷰에 투표했는지."""
