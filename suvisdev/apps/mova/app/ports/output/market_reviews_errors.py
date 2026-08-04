"""리뷰 도메인 예외 — 인바운드 라우터가 HTTPException으로 변환한다."""

from __future__ import annotations


class ReviewValidationError(Exception):
    """리뷰 저장 정책 위반(예: 별점·본문 둘 다 비어 있음)."""

    status_code = 422

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ReviewNotWatchedError(Exception):
    """watched 게이트 위반 — 시청 기록 없이 리뷰를 남기려는 시도(권한 성격이라 403)."""

    status_code = 403

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail
