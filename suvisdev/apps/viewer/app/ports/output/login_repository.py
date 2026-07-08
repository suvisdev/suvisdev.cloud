from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.auth_command_dto import LoginResponseDto, LoginUserCommand


class LoginRepository(ABC):
    """viewer 로그인 출력 포트 (ABC)."""

    @abstractmethod
    async def login_user(self, command: LoginUserCommand) -> LoginResponseDto:
        pass
