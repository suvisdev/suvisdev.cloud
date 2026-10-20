"""덜미 앱 레이어 예외 — 인터랙터는 HTTPException을 모른다(suvisdev/CLAUDE.md §K).
라우터가 이 예외를 HTTP 상태로 바꾼다."""

from __future__ import annotations


class UnknownSiteError(LookupError):
    """없거나 비활성인 공개 키 → 401."""


class OriginNotAllowedError(PermissionError):
    """등록 도메인 밖에서 온 호출 → 403."""


class BadSecretError(PermissionError):
    """비밀 키 불일치(또는 토큰의 사이트가 사라짐) → 401."""


class TokenExpiredError(ValueError):
    """점수 토큰 만료 → 400."""


class TokenInvalidError(ValueError):
    """서명이 틀리거나 형식이 깨진 토큰 → 401."""


class TokenReusedError(ValueError):
    """이미 검증에 쓴 토큰(리플레이) → 400."""


class TokenStoreUnavailableError(RuntimeError):
    """사용한 토큰 기록소(Redis)에 닿지 못함 → 503. 재사용을 못 막으니 통과시키지 않는다."""
