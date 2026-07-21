from __future__ import annotations

import logging

from viewer.app.dtos.oauth_dto import OAuthCallbackResultDto, SessionPayloadDto
from viewer.app.ports.input.oauth_login_use_case import OAuthLoginUseCase
from viewer.app.ports.output.oauth_errors import OAuthError
from viewer.app.ports.output.oauth_identity_repository import OAuthIdentityRepository
from viewer.app.ports.output.oauth_provider_port import OAuthProviderPort
from viewer.app.ports.output.pending_identity_repository import PendingIdentityRepository
from viewer.app.ports.output.session_store_port import SessionStorePort

logger = logging.getLogger(__name__)


class OAuthLoginInteractor(OAuthLoginUseCase):
    def __init__(
        self,
        *,
        providers: dict[str, OAuthProviderPort],
        identity_repository: OAuthIdentityRepository,
        pending_repository: PendingIdentityRepository,
        session_store: SessionStorePort,
    ) -> None:
        self._providers = providers
        self._identity_repository = identity_repository
        self._pending_repository = pending_repository
        self._session_store = session_store

    def _provider(self, provider: str) -> OAuthProviderPort:
        adapter = self._providers.get(provider)
        if adapter is None:
            raise OAuthError(f"지원하지 않는 로그인 방식입니다: {provider}", status_code=404)
        return adapter

    def build_authorize_url(self, *, provider: str, state: str) -> str:
        return self._provider(provider).build_authorize_url(state=state)

    async def handle_callback(self, *, provider: str, code: str) -> OAuthCallbackResultDto:
        identity = await self._provider(provider).exchange_code(code=code)

        existing = await self._identity_repository.find_linked_user(identity)
        if existing is not None:
            handoff_code = self._session_store.issue_session(
                user_id=existing.user_id, username=existing.username, email=identity.email
            )
            logger.info(
                "[OAuthLoginInteractor] %s 기존 계정 로그인 — user_id=%s",
                provider, existing.user_id,
            )
            return OAuthCallbackResultDto(kind="session", code=handoff_code)

        pending_code = self._pending_repository.save_pending(identity)
        logger.info("[OAuthLoginInteractor] %s 신규 신원 — 약관 동의 대기", provider)
        return OAuthCallbackResultDto(kind="consent_required", code=pending_code)

    def redeem(self, *, code: str) -> SessionPayloadDto | None:
        return self._session_store.redeem_handoff_code(code=code)

    async def complete_consent(self, *, code: str, agreed: bool) -> SessionPayloadDto | None:
        identity = self._pending_repository.pop_pending(code=code)
        if identity is None:
            return None
        if not agreed:
            logger.info("[OAuthLoginInteractor] %s 약관 동의 거부 — 계정 생성 취소", identity.provider)
            return None

        login = await self._identity_repository.create_linked_user(identity)
        handoff_code = self._session_store.issue_session(
            user_id=login.user_id, username=login.username, email=identity.email
        )
        session = self._session_store.redeem_handoff_code(code=handoff_code)
        if session is None:
            raise RuntimeError("방금 발급한 세션을 즉시 교환하지 못했습니다.")
        return session
