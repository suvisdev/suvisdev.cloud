from __future__ import annotations

import logging

from viewer.adapter.inbound.api.schemas.signup_schema import SignupSchema
from viewer.app.dtos.auth_command_dto import SignupCommand, SignupResponseDto
from viewer.app.ports.input.signup_use_case import SignupUseCase
from viewer.app.ports.output.signup_repository import SignupRepository

logger = logging.getLogger(__name__)


class SignupInteractor(SignupUseCase):
    """signup_router → 입력 포트 → 출력 포트(repository) → DB."""

    def __init__(self, repository: SignupRepository) -> None:
        self._repository = repository

    async def signup(self, payload: SignupSchema) -> SignupResponseDto:
        
        return SignupResponseDto(user_id=await self._repository.save_user(SignupCommand.from_schema(payload)))
