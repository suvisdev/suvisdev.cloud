"""계정 HTTP API /api/auth/* — 쿠키·CSRF·Origin(SECURITY.md 2절 '클라이언트 보관', 4절 'CSRF·CORS', 검증 13·26).

- 웹: __Host- 쿠키(HttpOnly·Secure·SameSite=Lax·Path=/), 토큰을 본문·localStorage에 두지 않는다.
  쿠키로 상태를 바꾸는 요청은 Origin == 공개 원점 + 이중 제출 CSRF(__Host-kcsrf 쿠키 = X-CSRF 머리글).
- 앱: X-Kumoniji-Client: app 머리글 → 토큰을 본문으로 주고 Authorization: Bearer로 받는다(쿠키 없음 → CSRF 면제).
  다른 사이트의 브라우저는 이 사용자 정의 머리글을 CORS 없이 보낼 수 없다.
"""

import hmac
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import db, passwords, service, sessions

router = APIRouter(prefix="/api/auth")
ACCESS, REFRESH, CSRF = "__Host-kat", "__Host-krt", "__Host-kcsrf"
REFRESH_AGE = 30 * 24 * 3600
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def origin() -> str:
    return os.environ.get("KUMONIJI_PUBLIC_ORIGIN", "https://kumoniji.suvisdev.cloud").rstrip("/")


def client_ip(request: Request) -> str:
    # 터널(Cloudflare) 뒤 — 서비스는 터널로만 들어온다. 외부 입력의 X-Forwarded-For는 쓰지 않는다.
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "")


def device_of(request: Request) -> str:
    return request.headers.get("x-kumoniji-device") or request.headers.get("user-agent", "")[:200]


def lang_of(request: Request) -> str:
    a = request.headers.get("accept-language", "en")[:2].lower()
    return a if a in ("ko", "en", "ja") else "en"


def is_app(request: Request) -> bool:
    return request.headers.get("x-kumoniji-client") == "app"


def check_csrf(request: Request) -> None:
    """쿠키 인증 + 상태 변경이면 Origin과 이중 제출 토큰을 모두 확인."""
    if request.method not in UNSAFE or is_app(request):
        return
    if request.headers.get("origin") != origin():
        raise HTTPException(403, {"code": "origin"})
    c, h = request.cookies.get(CSRF, ""), request.headers.get("x-csrf", "")
    if not c or not hmac.compare_digest(c, h):
        raise HTTPException(403, {"code": "csrf"})


def _token(request: Request) -> str | None:
    if is_app(request):
        h = request.headers.get("authorization", "")
        return h[7:] if h.lower().startswith("bearer ") else None
    return request.cookies.get(ACCESS)


def session_of(request: Request, allow_pre_mfa: bool = False, require_verified: bool = True) -> dict:
    """보호 API 공통 검사. DB 확인이 안 되면(장애 포함) 401 — 실패 쪽으로 닫힘(SECURITY 12).
    주의: FastAPI Depends로 직접 쓰지 않는다 — 기본값 인자가 쿼리 파라미터가 되어 ?allow_pre_mfa=true로 우회된다.
    의존성은 요청만 받는 player()를 쓴다."""
    check_csrf(request)
    try:
        with db.tx() as c:
            s = sessions.current(c, _token(request))
    except Exception:
        raise HTTPException(401, {"code": "session"}) from None
    if s is None:
        raise HTTPException(401, {"code": "session"})
    if not allow_pre_mfa and s["mfa_enabled"] and not s["mfa_passed"]:
        raise HTTPException(403, {"code": "mfa"})
    if require_verified and not s["verified"]:
        raise HTTPException(403, {"code": "unverified"})
    return s


def player(request: Request) -> dict:
    """의존성용: 인증된·MFA 통과 세션(게임 API·계정 설정)."""
    return session_of(request)


def _set_tokens(resp: Response, request: Request, out: dict) -> Response:
    if is_app(request):
        return resp
    resp.set_cookie(
        ACCESS, out["access"], max_age=sessions.ACCESS_TTL, path="/", secure=True, httponly=True, samesite="lax"
    )
    resp.set_cookie(REFRESH, out["refresh"], max_age=REFRESH_AGE, path="/", secure=True, httponly=True, samesite="lax")
    return resp


def _clear_tokens(resp: Response) -> Response:
    for name in (ACCESS, REFRESH):
        resp.delete_cookie(name, path="/", secure=True, httponly=True, samesite="lax")
    return resp


def _session_body(request: Request, out: dict) -> dict:
    body = {"mfa_required": out.get("mfa_required", False), "verified": out.get("verified", True)}
    if is_app(request) and "access" in out:
        body |= {"access": out["access"], "refresh": out["refresh"]}
    return body


def _http(e: Exception) -> HTTPException:
    """서비스 예외 → HTTP. 문구는 앱이 code로 언어별로 바꾼다."""
    if isinstance(e, service.Denied):
        return HTTPException(401, {"code": "credentials"})
    if isinstance(e, service.Wait):
        return HTTPException(429, {"code": "wait", "seconds": e.seconds})
    if isinstance(e, service.NeedCaptcha):
        return HTTPException(429, {"code": "captcha"})
    if isinstance(e, service.BadInput):
        return HTTPException(422, {"code": e.code})
    if isinstance(e, service.Forbidden):
        return HTTPException(403, {"code": e.code})
    return HTTPException(503, {"code": "busy"})


# 실패 기록(시도 제한)은 남겨야 하므로 커밋하고 응답한다. 나머지 오류는 롤백(예: 비밀번호 형식이 틀려도 인증 토큰이 닳지 않게).
KEEP = (service.Denied, service.Wait, service.NeedCaptcha)
ROLLBACK = (service.BadInput, service.Forbidden, passwords.Busy)


def _tx(fn):
    kept = None
    try:
        with db.tx() as c:
            try:
                return fn(c)
            except KEEP as e:
                kept = e
    except ROLLBACK as e:
        raise _http(e) from None
    raise _http(kept) from None


class Signup(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=600)
    nickname: str = Field(max_length=64)


class Login(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=600)
    captcha: str | None = Field(default=None, max_length=2048)


class TokenPassword(BaseModel):
    token: str = Field(max_length=200)
    password: str = Field(max_length=600)


class Email(BaseModel):
    email: str = Field(max_length=320)


class Password(BaseModel):
    password: str = Field(max_length=600)


class Refresh(BaseModel):
    refresh: str | None = Field(default=None, max_length=200)


@router.get("/config")
def config():
    """앱이 고를 로그인 수단. 비밀값은 없다(Turnstile 사이트 키는 공개용)."""
    return {
        "google": bool(os.environ.get("KUMONIJI_GOOGLE_CLIENT_ID")),
        "turnstile_site": os.environ.get("KUMONIJI_TURNSTILE_SITE", ""),
    }


@router.get("/csrf")
def csrf(request: Request, response: Response):
    """웹 앱이 시작할 때 한 번 받는다. 쿠키와 같은 값을 X-CSRF 머리글로 보낸다.
    이미 쿠키가 있으면 그 값을 그대로 준다 — 쿠키는 탭끼리 공유하므로 새로 만들면 먼저 연 탭이 403이 된다."""
    have = request.cookies.get(CSRF, "")
    value = (
        have
        if 32 <= len(have) <= 64 and have.replace("-", "").replace("_", "").isalnum()
        else secrets.token_urlsafe(32)
    )
    response.set_cookie(CSRF, value, path="/", secure=True, httponly=False, samesite="lax")
    return {"csrf": value}


@router.post("/signup", status_code=202)
def signup(body: Signup, request: Request):
    check_csrf(request)
    _tx(lambda c: service.signup(c, body.email, body.password, body.nickname, client_ip(request), lang_of(request)))
    return {"status": "check_email"}


@router.post("/verify")
def verify(body: TokenPassword, request: Request):
    check_csrf(request)
    _tx(lambda c: service.verify(c, body.token, body.password))
    return {"status": "verified"}


@router.get("/verify/check")
def verify_check(token: str):
    """링크 화면이 토큰이 아직 유효한지 묻는다(소비 안 함 — 메일 스캐너의 GET 대비)."""
    from . import tokens

    with db.tx() as c:
        return {"valid": tokens.peek(c, token, "verify")}


@router.post("/resend", status_code=202)
def resend(body: Email, request: Request):
    check_csrf(request)
    _tx(lambda c: service.resend_verify(c, body.email, client_ip(request), lang_of(request)))
    return {"status": "check_email"}


@router.post("/login")
def login(body: Login, request: Request):
    check_csrf(request)
    out = _tx(
        lambda c: service.login(
            c,
            body.email,
            body.password,
            client_ip(request),
            device_of(request),
            body.captcha,
            lang_of(request),
            captcha_capable=not is_app(request),
        )
    )
    resp = JSONResponse(_session_body(request, out))
    return _set_tokens(resp, request, out) if "access" in out else resp


@router.post("/refresh")
def refresh(request: Request, body: Refresh | None = None):
    check_csrf(request)
    raw = (body.refresh if body else None) if is_app(request) else request.cookies.get(REFRESH)
    with db.tx() as c:
        try:
            out = sessions.refresh(c, raw or "")
        except sessions.Reused:  # 전 세션 폐기를 커밋해야 하므로 트랜잭션 안에서 잡는다
            out = None
        except sessions.Raced:  # 다른 탭이 방금 갱신 — 공유 쿠키로 원래 요청을 다시 보내면 된다
            return JSONResponse({"code": "rotated"}, status_code=409)
    if out is None:
        return _clear_tokens(JSONResponse({"code": "session"}, status_code=401))
    access, new = out
    data = {"access": access, "refresh": new}
    return _set_tokens(JSONResponse(_session_body(request, data)), request, data)


@router.post("/logout")
def logout(request: Request):
    s = session_of(request, allow_pre_mfa=True, require_verified=False)
    with db.tx() as c:
        sessions.revoke(c, s["account_id"], s["sid"])
    return _clear_tokens(JSONResponse({"status": "ok"}))


@router.post("/logout-all")
def logout_all(request: Request):
    s = session_of(request, allow_pre_mfa=True, require_verified=False)
    with db.tx() as c:
        sessions.revoke_all(c, s["account_id"])
    return _clear_tokens(JSONResponse({"status": "ok"}))


@router.get("/me")
def me(request: Request):
    s = session_of(request, allow_pre_mfa=True, require_verified=False)
    with db.tx() as c:
        a = c.execute(
            """SELECT a.id, a.email, a.nickname, a.mfa_enabled, a.pw_hash IS NOT NULL AS has_password,
                      array(SELECT provider FROM identities WHERE account_id = a.id) AS providers
               FROM accounts a WHERE a.id = %s""",
            (s["account_id"],),
        ).fetchone()
    return {
        "id": a["id"],
        "email": a["email"],
        "nickname": a["nickname"],
        "mfa_enabled": a["mfa_enabled"],
        "mfa_passed": s["mfa_passed"],
        "has_password": a["has_password"],
        "providers": a["providers"],
    }


@router.get("/sessions")
def list_sessions(s: dict = Depends(player)):
    with db.tx() as c:
        rows = sessions.listing(c, s["account_id"])
    return [r | {"current": r["id"] == s["sid"]} for r in rows]


@router.delete("/sessions/{sid}")
def end_session(sid: str, s: dict = Depends(player)):
    with db.tx() as c:
        sessions.revoke(c, s["account_id"], sid)
    return {"status": "ok"}


@router.post("/reset/request", status_code=202)
def reset_request(body: Email, request: Request):
    check_csrf(request)
    _tx(lambda c: service.reset_request(c, body.email, client_ip(request), lang_of(request)))
    return {"status": "check_email"}


@router.get("/reset/check")
def reset_check(token: str):
    from . import tokens

    with db.tx() as c:
        return {"valid": tokens.peek(c, token, "reset")}


@router.post("/reset")
def reset(body: TokenPassword, request: Request):
    check_csrf(request)
    _tx(lambda c: service.reset(c, body.token, body.password, lang_of(request)))
    return _clear_tokens(JSONResponse({"status": "reset"}))


@router.post("/reauth")
def reauth(body: Password, request: Request):
    s = session_of(request, allow_pre_mfa=True)
    _tx(lambda c: service.reauth(c, s, body.password))
    return {"status": "ok"}


@router.post("/password")
def change_password(body: Password, request: Request):
    s = session_of(request)
    out = _tx(
        lambda c: service.change_password(c, s, body.password, device_of(request), client_ip(request), lang_of(request))
    )
    return _set_tokens(JSONResponse(_session_body(request, out)), request, out)


# ---- 구글 로그인 (검증 9·10) --------------------------------------------------------------------
GOOGLE_FLOW = "__Host-kgo"


@router.get("/google/start")
def google_start(request: Request, link: bool = False, reauth: bool = False):
    """웹: 구글로 보낸다. link=true면 로그인한 계정에 연결(최근 재인증·MFA 필요),
    reauth=true면 구글로 다시 인증(비밀번호 없는 계정의 탈퇴 등 민감 작업용)."""
    from fastapi.responses import RedirectResponse

    from . import google

    account_id = sid = None
    purpose = "login"
    if link:
        s = session_of(request)
        _tx(lambda c: service.require_recent(s))
        account_id, sid, purpose = s["account_id"], s["sid"], "link"
    elif reauth:
        s = session_of(request, allow_pre_mfa=True)
        account_id, sid, purpose = s["account_id"], s["sid"], "reauth"
    try:
        url, flow = google.start(origin(), purpose, account_id, sid)
    except google.Invalid:
        raise HTTPException(503, {"code": "google_not_configured"}) from None
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie(GOOGLE_FLOW, flow, max_age=google.FLOW_TTL, path="/", secure=True, httponly=True, samesite="lax")
    return resp


@router.get("/google/callback")
def google_callback(request: Request, code: str = "", state: str = ""):
    """구글이 돌려보내는 곳. state·PKCE·nonce를 흐름 쿠키와 대조한 뒤에만 로그인·연결."""
    from fastapi.responses import RedirectResponse

    from . import google

    fail = RedirectResponse("/?auth_error=google", status_code=302)
    fail.delete_cookie(GOOGLE_FLOW, path="/", secure=True, httponly=True, samesite="lax")
    try:
        f = google.read_flow(request.cookies.get(GOOGLE_FLOW), state)
        claims = google.verify_id_token(google.exchange(code[:2048], f["pv"], origin()), f["no"])
    except google.Invalid:
        return fail
    try:
        with db.tx() as c:
            if f["pu"] == "link":
                google.link(c, f["ac"], f["si"], claims)
                out = None
            elif f["pu"] == "reauth":
                google.reauth(c, f["ac"], f["si"], claims)
                out = None
            else:
                aid = google.find_or_create(c, claims)
                row = c.execute(
                    "SELECT id, email, mfa_enabled FROM accounts WHERE id = %s AND locked_at IS NULL", (aid,)
                ).fetchone()
                if row is None:
                    return fail
                out = service._open_session(c, row, device_of(request), client_ip(request), lang_of(request))
    except google.Invalid:
        return fail
    done = {"link": "/?linked=google", "reauth": "/?reauthed=google"}.get(f["pu"], "/")
    resp = RedirectResponse(done, status_code=302)
    resp.delete_cookie(GOOGLE_FLOW, path="/", secure=True, httponly=True, samesite="lax")
    return _set_tokens(resp, request, out) if out else resp


class GoogleApp(BaseModel):
    id_token: str = Field(max_length=4096)
    nonce: str = Field(min_length=16, max_length=200)


@router.post("/google/app")
def google_app(body: GoogleApp, request: Request):
    """앱(안드로이드): 앱이 받은 ID 토큰을 서버가 같은 방식으로 검증."""
    from . import google

    if not is_app(request):
        raise HTTPException(403, {"code": "app_only"})
    try:
        claims = google.verify_id_token(body.id_token, body.nonce)
    except google.Invalid:
        raise HTTPException(401, {"code": "google"}) from None
    with db.tx() as c:
        aid = google.find_or_create(c, claims)
        row = c.execute(
            "SELECT id, email, mfa_enabled FROM accounts WHERE id = %s AND locked_at IS NULL", (aid,)
        ).fetchone()
        if row is None:
            raise HTTPException(401, {"code": "google"})
        out = service._open_session(c, row, device_of(request), client_ip(request), lang_of(request))
    return _session_body(request, out)


@router.post("/google/unlink")
def google_unlink(request: Request):
    from . import google

    s = session_of(request)
    try:
        _tx(lambda c: (service.require_recent(s), google.unlink(c, s["account_id"])))
    except google.Invalid:
        raise HTTPException(409, {"code": "last_method"}) from None
    return {"status": "ok"}


# ---- 2단계 인증 (검증 7·8) ----------------------------------------------------------------------


class Code(BaseModel):
    code: str = Field(max_length=32)


@router.post("/mfa/setup")
def mfa_setup(request: Request):
    from . import mfa

    s = session_of(request)
    return _tx(lambda c: mfa.setup(c, s))


@router.post("/mfa/enable")
def mfa_enable(body: Code, request: Request):
    from . import mfa

    s = session_of(request)
    return {"recovery_codes": _tx(lambda c: mfa.enable(c, s, body.code, lang_of(request)))}


@router.post("/mfa/verify")
def mfa_verify(body: Code, request: Request):
    from . import mfa

    s = session_of(request, allow_pre_mfa=True)
    _tx(lambda c: mfa.verify(c, s, body.code))
    return {"status": "ok"}


@router.post("/mfa/disable")
def mfa_disable(body: Code, request: Request):
    from . import mfa

    s = session_of(request)
    _tx(lambda c: mfa.disable(c, s, body.code, lang_of(request)))
    return {"status": "ok"}


@router.post("/mfa/recovery")
def mfa_recovery(request: Request):
    from . import mfa

    s = session_of(request)
    return {"recovery_codes": _tx(lambda c: mfa.regenerate(c, s, lang_of(request)))}


# ---- 주소 변경·보호 (검증 6) --------------------------------------------------------------------


class Token(BaseModel):
    token: str = Field(max_length=200)


@router.post("/email", status_code=202)
def change_email(body: Email, request: Request):
    s = session_of(request)
    _tx(lambda c: service.change_email(c, s, body.email, lang_of(request)))
    return {"status": "check_email"}


@router.post("/email/confirm")
def confirm_email(body: Token, request: Request):
    check_csrf(request)
    _tx(lambda c: service.confirm_email(c, body.token, lang_of(request)))
    return {"status": "changed"}


@router.get("/protect/check")
def protect_check(token: str):
    from . import tokens

    with db.tx() as c:
        return {"valid": tokens.peek(c, token, "protect")}


@router.post("/protect")
def protect(body: Token, request: Request):
    check_csrf(request)
    _tx(lambda c: service.protect(c, body.token))
    return _clear_tokens(JSONResponse({"status": "locked"}))


# ---- 탈퇴 (검증 8) ------------------------------------------------------------------------------


@router.post("/delete")
def delete_account(request: Request):
    s = session_of(request)
    _tx(lambda c: service.delete_account(c, s))
    return _clear_tokens(JSONResponse({"status": "deleted"}))
