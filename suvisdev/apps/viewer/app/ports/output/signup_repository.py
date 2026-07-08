from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.app.dtos.auth_command_dto import SignupCommand


class SignupRepository(ABC):
    """viewer 회원가입 출력 포트 (ABC)."""

    @abstractmethod
    async def save_user(self, command: SignupCommand) -> int:
        pass
