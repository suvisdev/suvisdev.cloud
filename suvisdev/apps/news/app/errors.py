"""news 앱 레이어 예외 — 인터랙터는 HTTPException을 모른다(suvisdev/CLAUDE.md §K).
라우터가 이 예외를 HTTP 상태로 바꾼다."""

from __future__ import annotations


class TopicNotFoundError(LookupError):
    """없거나 비공개인 검색어 탭 → 404."""


class TopicValidationError(ValueError):
    """검색어·이름 입력값 오류 → 400."""


class DuplicateTopicError(ValueError):
    """같은 검색어가 이미 있음 → 409."""
