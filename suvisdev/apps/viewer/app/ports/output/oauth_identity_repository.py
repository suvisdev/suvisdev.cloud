from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.auth_command_dto import LoginResponseDto
from viewer.app.dtos.oauth_dto import OAuthIdentity


class OAuthIdentityRepository(ABC):
    """OAuth로 확인된 신원을 로컬 users 계정과 연결(또는 신규 생성)하는 출력 포트."""

    @abstractmethod
    async def find_linked_user(self, identity: OAuthIdentity) -> LoginResponseDto | None:
        """이미 연결된 계정이 있으면 반환한다. 신규 생성은 하지 않는다."""

    @abstractmethod
    async def create_linked_user(self, identity: OAuthIdentity) -> LoginResponseDto:
        """약관 동의가 끝난 신규 신원을 위해 계정을 생성하고 연결한다."""
