from __future__ import annotations

from auth.kakao_mobile_verifier import KakaoMobileTokenVerifier
from auth.mobile_refresh_store import MobileRefreshTokenStore
from auth.oauth_adapters import OAuthError
from auth.oauth_adapters.google import GoogleOAuthAdapter
from auth.oauth_adapters.kakao import KakaoOAuthAdapter
from auth.oauth_adapters.naver import NaverOAuthAdapter
from auth.oauth_handoff_store import OAuthHandoffStore
from auth.oauth_state_store import OAuthStateStore
from auth.refresh_store import RefreshTokenStore, ReuseDetected
from auth.repository import UserRepository
from auth.schemas import KakaoMobileTokenResponse, TokenResponse
from auth.security import JwtAdapter

# security.py의 _ACCESS_TTL_DEFAULT_MIN와 같은 이유로 7일. refresh 흐름 도입
# 전까지 프론트에서 10분마다 401을 받아 재로그인이 유도되던 이슈의 즉시 fix.
_ACCESS_TTL_MIN = 60 * 24 * 7
_MOBILE_AUD = "suvis-susu"


class OAuthIdentityNotLinked(Exception):
    """조회된 OAuth identity가 아직 어떤 users 계정에도 연결돼 있지 않음.

    이번 라운드는 회원가입/자동연동을 하지 않는다 — viewer 쪽에서 이미 연동된
    identity만 로그인 성공한다."""


class InvalidCredentials(Exception):
    pass


class OAuthStateInvalid(Exception):
    """콜백으로 돌아온 state가 없거나, 발급된 적 없거나, 이미 소비됨(CSRF 의심)."""


class AuthService:
    def __init__(
        self,
        *,
        user_repository: UserRepository | None = None,
        token_issuer: JwtAdapter | None = None,
        refresh_store: RefreshTokenStore | None = None,
        oauth_adapters: dict[str, object] | None = None,
        oauth_state_store: OAuthStateStore | None = None,
        oauth_handoff_store: OAuthHandoffStore | None = None,
        kakao_mobile_verifier: KakaoMobileTokenVerifier | None = None,
        mobile_refresh_store: MobileRefreshTokenStore | None = None,
    ) -> None:
        self._users = user_repository or UserRepository()
        self._tokens = token_issuer or JwtAdapter()
        self._refresh = refresh_store or RefreshTokenStore()
        self._oauth_adapters = oauth_adapters or {
            "google": GoogleOAuthAdapter(),
            "kakao": KakaoOAuthAdapter(),
            "naver": NaverOAuthAdapter(),
        }
        self._oauth_state = oauth_state_store or OAuthStateStore()
        self._oauth_handoff = oauth_handoff_store or OAuthHandoffStore()
        self._kakao_mobile_verifier = kakao_mobile_verifier or KakaoMobileTokenVerifier()
        self._mobile_refresh = mobile_refresh_store or MobileRefreshTokenStore()

    def build_authorize_url(self, provider: str, state: str) -> str:
        adapter = self._get_oauth_adapter(provider)
        return adapter.build_authorize_url(state)

    def start_oauth_login(self, provider: str, aud: str, return_to: str | None = None) -> str:
        """provider 검증(미지원 시 OAuthError 404) + CSRF state 발급(aud/return_to 포함
        저장) 후 인증 URL 반환. aud/return_to는 프로바이더가 콜백에 실어 보내주지
        않으므로 여기서 state에 묶어 저장해뒀다가 콜백에서 state로 다시 꺼내 쓴다.
        return_to는 호출자(router)가 이미 화이트리스트 검증을 마친 값이어야 한다."""
        adapter = self._get_oauth_adapter(provider)
        state = self._oauth_state.issue(aud=aud, return_to=return_to)
        return adapter.build_authorize_url(state)

    async def login_with_password(self, username: str, password: str, aud: str) -> TokenResponse:
        user = await self._users.find_by_credentials(username, password)
        if user is None:
            raise InvalidCredentials("아이디 또는 비밀번호가 올바르지 않습니다.")
        return self._issue_token_pair(sub=str(user.user_id), roles=user.role_values(), aud=aud)

    async def signup(
        self, email: str, password: str, username: str | None, aud: str
    ) -> TokenResponse:
        """email 중복이면 EmailAlreadyExists(호출자가 409로 변환). 성공 시 곧바로
        토큰까지 발급해 가입과 동시에 로그인된 상태로 만든다."""
        resolved_username = username or email.split("@", 1)[0]
        user = await self._users.create_user(
            email=email, password=password, username=resolved_username
        )
        return self._issue_token_pair(sub=str(user.user_id), roles=user.role_values(), aud=aud)

    async def handle_oauth_callback(
        self, provider: str, code: str, state: str | None
    ) -> tuple[TokenResponse, str | None]:
        """반환값의 두 번째 요소(return_to)는 로그인 시작 시점에 state에 저장해둔
        값 그대로다 — 이미 router에서 화이트리스트 검증을 거친 값이므로 여기서는
        그대로 통과시킨다."""
        state_data = self._oauth_state.consume(state) if state else None
        if state_data is None:
            raise OAuthStateInvalid("state 값이 없거나 유효하지 않습니다(CSRF 의심).")

        adapter = self._get_oauth_adapter(provider)
        identity = await adapter.exchange_code(code)
        user = await self._users.find_by_oauth_identity(identity.provider, identity.provider_user_id)
        if user is None:
            raise OAuthIdentityNotLinked(
                f"{provider} 계정이 아직 연동되지 않았습니다. viewer에서 먼저 연동하세요."
            )
        token_response = self._issue_token_pair(
            sub=str(user.user_id), roles=user.role_values(), aud=state_data.aud
        )
        return token_response, state_data.return_to

    def create_oauth_handoff(self, token_response: TokenResponse) -> str:
        """콜백에서 발급한 토큰을 URL에 직접 싣지 않기 위한 1회용 code 발급(60초 TTL)."""
        return self._oauth_handoff.save(token_response)

    async def exchange_handoff(self, code: str) -> TokenResponse | None:
        return self._oauth_handoff.pop(code)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        rotated = self._refresh.rotate(jti=refresh_token)  # 재사용 시 ReuseDetected
        access_token = self._tokens.issue_access_token(
            sub=rotated.sub, roles=rotated.roles, aud=rotated.aud, expires_min=_ACCESS_TTL_MIN
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=rotated.jti,
            expires_in=_ACCESS_TTL_MIN * 60,
        )

    async def logout(self, refresh_token: str) -> None:
        try:
            rotated = self._refresh.rotate(jti=refresh_token)
            self._refresh.revoke_family(rotated.family_id)
        except ReuseDetected:
            pass  # 이미 무효화된 토큰 — 로그아웃 목적은 이미 달성된 상태

    async def login_with_kakao_mobile(self, access_token: str) -> KakaoMobileTokenResponse:
        """모바일(susu) 전용 — kapi로 access_token을 검증한 뒤 곧바로 계정을 만들거나
        조회한다(웹과 달리 자동 생성). 발급된 refresh token은 auth:refresh:mobile:{userId}
        네임스페이스에 저장되어 웹 세션과 완전히 분리된다."""
        identity = await self._kakao_mobile_verifier.verify(access_token)
        user = await self._users.find_or_create_by_kakao(
            provider_user_id=identity.provider_user_id,
            email=identity.email,
            nickname=identity.nickname,
        )
        access_jwt = self._tokens.issue_access_token(
            sub=str(user.user_id), roles=user.role_values(), aud=_MOBILE_AUD, expires_min=_ACCESS_TTL_MIN
        )
        refresh_token = self._mobile_refresh.issue(
            user_id=str(user.user_id), sub=str(user.user_id), aud=_MOBILE_AUD, roles=user.role_values()
        )
        return KakaoMobileTokenResponse(
            access_token=access_jwt,
            refresh_token=refresh_token,
            expires_in=_ACCESS_TTL_MIN * 60,
            nickname=identity.nickname,
        )

    async def mobile_refresh(self, refresh_token: str) -> TokenResponse:
        session = self._mobile_refresh.rotate(refresh_token=refresh_token)
        access_jwt = self._tokens.issue_access_token(
            sub=session.sub, roles=session.roles, aud=session.aud, expires_min=_ACCESS_TTL_MIN
        )
        return TokenResponse(
            access_token=access_jwt,
            refresh_token=session.refresh_token,
            expires_in=_ACCESS_TTL_MIN * 60,
        )

    async def mobile_logout(self, refresh_token: str) -> None:
        self._mobile_refresh.revoke(refresh_token=refresh_token)

    def _issue_token_pair(self, *, sub: str, roles: list[str], aud: str) -> TokenResponse:
        access_token = self._tokens.issue_access_token(
            sub=sub, roles=roles, aud=aud, expires_min=_ACCESS_TTL_MIN
        )
        refresh_jti, _ = self._refresh.issue(sub=sub, aud=aud, roles=roles)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_jti,
            expires_in=_ACCESS_TTL_MIN * 60,
        )

    def _get_oauth_adapter(self, provider: str) -> object:
        adapter = self._oauth_adapters.get(provider)
        if adapter is None:
            raise OAuthError(f"지원하지 않는 provider: {provider}", status_code=404)
        return adapter
