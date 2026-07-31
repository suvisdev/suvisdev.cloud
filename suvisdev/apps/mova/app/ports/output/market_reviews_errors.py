"""리뷰 도메인 예외 — 인바운드 라우터가 HTTPException으로 변환한다."""

from __future__ import annotations


class ReviewValidationError(Exception):
    """리뷰 저장 정책 위반(예: 별점·본문 둘 다 비어 있음)."""

    status_code = 422

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail
