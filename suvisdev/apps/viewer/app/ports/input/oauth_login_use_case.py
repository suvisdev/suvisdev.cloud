from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.oauth_dto import OAuthCallbackResultDto, SessionPayloadDto


class OAuthLoginUseCase(ABC):
    """viewer OAuth 로그인(google/naver/kakao) 입력 포트."""

    @abstractmethod
    def build_authorize_url(self, *, provider: str, state: str) -> str:
        pass

    @abstractmethod
    async def handle_callback(self, *, provider: str, code: str) -> OAuthCallbackResultDto:
        """코드 교환 → 신원 확인. 기존 연결 계정이면 세션 발급, 신규면 약관 동의 대기 코드 발급."""

    @abstractmethod
    def redeem(self, *, code: str) -> SessionPayloadDto | None:
        pass

    @abstractmethod
    async def complete_consent(self, *, code: str, agreed: bool) -> SessionPayloadDto | None:
        """약관 동의 완료 처리 — agreed=True일 때만 실제 계정을 생성하고 세션을 발급한다."""
