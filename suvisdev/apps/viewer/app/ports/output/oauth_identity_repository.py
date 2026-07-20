from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.auth_command_dto import LoginResponseDto
from viewer.app.dtos.oauth_dto import OAuthIdentity


class OAuthIdentityRepository(ABC):
    """OAuth로 확인된 신원을 로컬 users 계정과 연결(또는 신규 생성)하는 출력 포트."""

    @abstractmethod
    async def find_or_create_user(self, identity: OAuthIdentity) -> LoginResponseDto:
        pass
