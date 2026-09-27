from __future__ import annotations

from gildle.app.errors import PushTokenValidationError
from gildle.app.ports.input.push_token_use_case import PushTokenUseCase
from gildle.app.ports.output.push_token_repository import PushTokenRepositoryPort
from gildle.domain.entities.push_token_entity import PushToken


class PushTokenInteractor(PushTokenUseCase):
    """토큰 등록·해제. 발송은 아직 없다 — 보낼 알림이 정해지면 서비스 계정 키
    (`~/secrets/gildle-fcm.json`)로 FCM HTTP v1을 호출하는 출력 포트를 더한다."""

    def __init__(self, repository: PushTokenRepositoryPort) -> None:
        self._repository = repository

    async def register(self, user_id: int, token: str, platform: str) -> PushToken:
        try:
            entity = PushToken(id=None, user_id=user_id, token=token.strip(), platform=platform)
        except ValueError as e:
            raise PushTokenValidationError(str(e)) from e
        return await self._repository.upsert(entity)

    async def unregister(self, user_id: int, token: str) -> None:
        await self._repository.delete(user_id, token.strip())
