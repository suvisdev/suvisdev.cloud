from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.oauth_dto import SessionPayloadDto


class OAuthLoginUseCase(ABC):
    """viewer OAuth 로그인(google/naver/kakao) 입력 포트."""

    @abstractmethod
    def build_authorize_url(self, *, provider: str, state: str) -> str:
        pass

    @abstractmethod
    async def handle_callback(self, *, provider: str, code: str) -> str:
        """콜백 처리(코드 교환 → 사용자 연결 → 세션 발급) 후 1회용 handoff code를 반환한다."""

    @abstractmethod
    def redeem(self, *, code: str) -> SessionPayloadDto | None:
        pass
