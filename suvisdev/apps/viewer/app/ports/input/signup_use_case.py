from __future__ import annotations

from abc import ABC, abstractmethod

from viewer.adapter.inbound.api.schemas.signup_schema import SignupSchema
from viewer.app.dtos.auth_command_dto import SignupResponseDto


class SignupUseCase(ABC):
    """viewer 회원가입(POST) 입력 포트 (ABC)."""

    @abstractmethod
    async def signup(self, payload: SignupSchema) -> SignupResponseDto:
        pass
