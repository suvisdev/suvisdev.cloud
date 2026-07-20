from __future__ import annotations

import logging

from viewer.app.dtos.oauth_dto import SessionPayloadDto
from viewer.app.ports.input.oauth_login_use_case import OAuthLoginUseCase
from viewer.app.ports.output.oauth_errors import OAuthError
from viewer.app.ports.output.oauth_identity_repository import OAuthIdentityRepository
from viewer.app.ports.output.oauth_provider_port import OAuthProviderPort
from viewer.app.ports.output.session_store_port import SessionStorePort

logger = logging.getLogger(__name__)


class OAuthLoginInteractor(OAuthLoginUseCase):
    def __init__(
        self,
        *,
        providers: dict[str, OAuthProviderPort],
        identity_repository: OAuthIdentityRepository,
        session_store: SessionStorePort,
    ) -> None:
        self._providers = providers
        self._identity_repository = identity_repository
        self._session_store = session_store

    def _provider(self, provider: str) -> OAuthProviderPort:
        adapter = self._providers.get(provider)
        if adapter is None:
            raise OAuthError(f"지원하지 않는 로그인 방식입니다: {provider}", status_code=404)
        return adapter

    def build_authorize_url(self, *, provider: str, state: str) -> str:
        return self._provider(provider).build_authorize_url(state=state)

    async def handle_callback(self, *, provider: str, code: str) -> str:
        identity = await self._provider(provider).exchange_code(code=code)
        login = await self._identity_repository.find_or_create_user(identity)
        logger.info(
            "[OAuthLoginInteractor] %s 로그인 완료 — user_id=%s", provider, login.user_id
        )
        return self._session_store.issue_session(user_id=login.user_id, username=login.username)

    def redeem(self, *, code: str) -> SessionPayloadDto | None:
        return self._session_store.redeem_handoff_code(code=code)
