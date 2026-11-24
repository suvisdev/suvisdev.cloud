"""구글 로그인(OIDC) — SECURITY.md 2절 'OAuth·OIDC'·'계정 연결·해제', 검증 9·10.

웹: 인가 코드 + PKCE(S256) + state + nonce. 세 값은 서명된 10분 쿠키에 두고 콜백에서 대조한다.
ID 토큰은 구글 공개 키(JWKS)로 서명·RS256·iss·aud·exp·nonce·email_verified를 검증한다. 리디렉트 URI는 고정.
식별자는 (google, sub). 같은 이메일의 자체 계정이 있어도 자동으로 합치지 않는다.
"""

import base64
import hashlib
import os
import secrets
import time
from urllib.parse import urlencode

import httpx
import jwt
from psycopg import errors

AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
JWKS = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")
FLOW_TTL = 600
REAUTH_MAX_AGE = 300  # 최근 인증 5분(service.REAUTH_SECONDS와 같음)
_jwks = jwt.PyJWKClient(JWKS, cache_keys=True, lifespan=3600, timeout=5)


class Invalid(Exception):
    pass


def client_id() -> str:
    return os.environ.get("KUMONIJI_GOOGLE_CLIENT_ID", "")


def redirect_uri(origin: str) -> str:
    return origin + "/api/auth/google/callback"


def _flow_key() -> bytes:
    return hashlib.sha256(b"google-flow:" + os.environ.get("KUMONIJI_JWT_SECRET", "").encode()).digest()


def start(
    origin: str, purpose: str = "login", account_id: int | None = None, sid: str | None = None, lang: str = "en"
) -> tuple[str, str]:
    """(구글로 보낼 URL, 흐름 쿠키 값). purpose: login, link(로그인한 계정에 연결), reauth(구글로 다시 인증)."""
    if not client_id():
        raise Invalid("not_configured")
    state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    flow = jwt.encode(
        {
            "st": state,
            "no": nonce,
            "pv": verifier,
            "pu": purpose,
            "ac": account_id,
            "si": sid,
            "la": lang,
            "exp": int(time.time()) + FLOW_TTL,
        },
        _flow_key(),
        "HS256",
    )
    q = {
        "client_id": client_id(),
        "redirect_uri": redirect_uri(origin),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    if purpose == "reauth":
        q["max_age"] = "0"  # 구글에서 실제로 다시 로그인하게 한다(auth_time으로 확인)
    return f"{AUTH}?{urlencode(q)}", flow


def read_flow(flow: str | None, state: str | None) -> dict:
    try:
        f = jwt.decode(flow or "", _flow_key(), algorithms=["HS256"], options={"require": ["exp"]})
    except jwt.PyJWTError:
        raise Invalid("flow") from None
    if not state or not secrets.compare_digest(f["st"], state):
        raise Invalid("state")
    return f


def exchange(code: str, verifier: str, origin: str, client: httpx.Client | None = None) -> str:
    """인가 코드 → ID 토큰(서버 간 요청, 비밀은 서버만 앎)."""
    try:
        r = (client or httpx).post(
            TOKEN,
            data={
                "code": code,
                "client_id": client_id(),
                "client_secret": os.environ.get("KUMONIJI_GOOGLE_CLIENT_SECRET", ""),
                "redirect_uri": redirect_uri(origin),
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            },
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["id_token"]
    except (httpx.HTTPError, KeyError, ValueError):
        raise Invalid("exchange") from None


def verify_id_token(token: str, nonce: str, key=None) -> dict:
    """서명(RS256만)·iss·aud·exp·nonce·email_verified. 키를 못 받으면 거부."""
    try:
        signing = key or _jwks.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing,
            algorithms=["RS256"],
            audience=client_id(),
            options={"require": ["exp", "iss", "aud", "sub", "nonce"]},
        )
    except (jwt.PyJWTError, httpx.HTTPError):
        raise Invalid("id_token") from None
    if claims["iss"] not in ISSUERS or not secrets.compare_digest(str(claims["nonce"]), nonce):
        raise Invalid("id_token")
    return claims


def find_or_create(c, claims: dict) -> int:
    """(google, sub)로 계정을 찾고, 없으면 새 계정. 같은 이메일의 자체 계정과 자동 병합하지 않는다 →
    새 계정의 이메일 칸은 비워 둔다(기존 계정 주인은 로그인 후 설정에서 연결)."""
    # 같은 구글 계정의 첫 로그인이 동시에 오면 둘 다 "없음"으로 보고 만들다 충돌한다 → sub별로 줄 세움
    c.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("google:" + claims["sub"],))
    row = c.execute(
        """SELECT i.account_id FROM identities i JOIN accounts a ON a.id = i.account_id
           WHERE i.provider = 'google' AND i.sub = %s AND a.deleted_at IS NULL""",
        (claims["sub"],),
    ).fetchone()
    if row:
        return row["account_id"]
    email = claims.get("email") if claims.get("email_verified") else None
    nick = (claims.get("given_name") or claims.get("name") or "player")[:16]

    def create(e):
        return c.execute(
            "INSERT INTO accounts (email, email_key, nickname, verified_at) VALUES (%s, %s, %s, now()) RETURNING id",
            (e, e and e.lower(), nick),
        ).fetchone()["id"]

    try:
        with c.transaction():
            aid = create(email)
    except errors.UniqueViolation:  # 그 주소의 계정이 이미 있음(동시 가입 포함) — 병합하지 않으니 이메일 없이
        aid = create(None)
    c.execute("INSERT INTO identities VALUES ('google', %s, %s)", (claims["sub"], aid))
    return aid


def link(c, account_id: int, sid: str, claims: dict) -> None:
    """로그인한 계정에 구글 연결. 다른 계정에 이미 연결된 sub면 거부.
    구글에 다녀오는 사이 그 세션이 폐기됐거나(비밀번호 변경·전체 로그아웃) 최근 인증·MFA가 풀렸으면 거부 —
    탈취된 세션으로 시작한 연결이 폐기 뒤에 완료되면 공격자의 구글로 다시 들어올 수 있다."""
    if not c.execute(
        """SELECT 1 FROM sessions s JOIN accounts a ON a.id = s.account_id
           WHERE s.id = %s AND s.account_id = %s AND s.revoked_at IS NULL AND a.deleted_at IS NULL
             AND a.locked_at IS NULL AND s.reauth_at > now() - %s * interval '1 second'
             AND (NOT a.mfa_enabled OR s.mfa_passed)""",
        (sid, account_id, REAUTH_MAX_AGE),
    ).fetchone():
        raise Invalid("session")
    owner = c.execute(
        "SELECT account_id FROM identities WHERE provider = 'google' AND sub = %s", (claims["sub"],)
    ).fetchone()
    if owner and owner["account_id"] != account_id:
        raise Invalid("taken")
    if not owner:
        c.execute("INSERT INTO identities VALUES ('google', %s, %s)", (claims["sub"], account_id))


def unlink(c, account_id: int) -> None:
    """마지막 로그인 수단은 지우지 않는다(비밀번호도 없고 다른 제공자도 없으면 거부)."""
    a = c.execute(
        """SELECT pw_hash IS NOT NULL AND verified_at IS NOT NULL AS has_pw,
                  (SELECT count(*) FROM identities WHERE account_id = %s AND provider <> 'google') AS others
           FROM accounts WHERE id = %s""",
        (account_id, account_id),
    ).fetchone()
    if not a["has_pw"] and not a["others"]:
        raise Invalid("last_method")
    c.execute("DELETE FROM identities WHERE account_id = %s AND provider = 'google'", (account_id,))


def reauth(c, account_id: int, sid: str, claims: dict) -> None:
    """구글로 방금 다시 로그인했음을 확인(이 계정에 연결된 sub, auth_time 5분 이내) → 세션의 최근 인증 갱신."""
    if (claims.get("auth_time") or 0) < time.time() - REAUTH_MAX_AGE:
        raise Invalid("stale")
    if not c.execute(
        "SELECT 1 FROM identities WHERE provider = 'google' AND sub = %s AND account_id = %s",
        (claims["sub"], account_id),
    ).fetchone():
        raise Invalid("not_linked")
    if not c.execute(
        "UPDATE sessions SET reauth_at = now() WHERE id = %s AND account_id = %s AND revoked_at IS NULL RETURNING 1",
        (sid, account_id),
    ).fetchone():
        raise Invalid("session")
