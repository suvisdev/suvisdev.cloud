from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)
    aud: str = Field(..., min_length=1, description="토큰을 발급받을 대상 서비스 (예: suvis-mova)")


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    username: str | None = Field(default=None, min_length=1, max_length=50)
    aud: str = Field(..., min_length=1, description="가입 즉시 자동 로그인할 대상 서비스")

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("올바른 이메일 형식이 아닙니다.")
        return value


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class OAuthExchangeRequest(BaseModel):
    code: str = Field(..., min_length=1)


class KakaoMobileLoginRequest(BaseModel):
    access_token: str = Field(
        ..., min_length=1, description="kakao_flutter_sdk 로그인 결과의 access token"
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class KakaoMobileTokenResponse(TokenResponse):
    """모바일 로그인 응답 — 클라가 별도로 me()를 호출하지 않도록 표시용 닉네임을 함께 준다."""

    nickname: str | None = None


class TokenPayload(BaseModel):
    sub: str
    roles: list[str]
    aud: str
    exp: int
    iat: int
    jti: str


class MobileEmailRequest(BaseModel):
    """앱 이메일 회원가입·로그인 — 필수 항목(이메일·비밀번호)만 받는다(2026-09-28)."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL_RE.match(value):
            raise ValueError("올바른 이메일 형식이 아닙니다.")
        return value
