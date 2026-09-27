"""gildle 앱 레이어 예외 — 인터랙터는 HTTPException을 모른다(suvisdev/CLAUDE.md §K).
라우터가 이 예외를 HTTP 상태로 바꾼다(2026-09-27 아키텍처 감사에서 수정)."""

from __future__ import annotations


class WalkValidationError(ValueError):
    """산책 기록 입력값 오류 → 400."""


class WalkNotFoundError(LookupError):
    """없거나 남의 기록 → 404(존재 여부를 흘리지 않는다)."""


class PushTokenValidationError(ValueError):
    """푸시 토큰 입력값 오류 → 400."""
