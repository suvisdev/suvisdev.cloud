from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_viewer_db
from viewer.adapter.outbound.cache.redis_session_store_adapter import RedisSessionStoreAdapter
from viewer.adapter.outbound.oauth.google_oauth_adapter import GoogleOAuthAdapter
from viewer.adapter.outbound.oauth.kakao_oauth_adapter import KakaoOAuthAdapter
from viewer.adapter.outbound.oauth.naver_oauth_adapter import NaverOAuthAdapter
from viewer.adapter.outbound.pg.oauth_identity_pg_repository import OAuthIdentityPgRepository
from viewer.app.ports.input.oauth_login_use_case import OAuthLoginUseCase
from viewer.app.ports.output.oauth_identity_repository import OAuthIdentityRepository
from viewer.app.ports.output.oauth_provider_port import OAuthProviderPort
from viewer.app.ports.output.session_store_port import SessionStorePort
from viewer.app.use_cases.oauth_login_interactor import OAuthLoginInteractor

_PROVIDER_REGISTRY: dict[str, type[OAuthProviderPort]] = {
    "google": GoogleOAuthAdapter,
    "kakao": KakaoOAuthAdapter,
    "naver": NaverOAuthAdapter,
}


def get_oauth_login_use_case(db: AsyncSession = Depends(get_viewer_db)) -> OAuthLoginUseCase:
    providers: dict[str, OAuthProviderPort] = {
        key: adapter_cls() for key, adapter_cls in _PROVIDER_REGISTRY.items()
    }
    identity_repository: OAuthIdentityRepository = OAuthIdentityPgRepository(session=db)
    session_store: SessionStorePort = RedisSessionStoreAdapter()
    return OAuthLoginInteractor(
        providers=providers,
        identity_repository=identity_repository,
        session_store=session_store,
    )
