"""계정 규칙(SECURITY.md 1절): 가입·인증·로그인·재설정·비밀번호 변경. HTTP는 web.py, 여기는 DB 연결(c)만 받는다."""

import hashlib
from datetime import timedelta

from psycopg import errors

from . import limits, mail, passwords, sessions, tokens

VERIFY_TTL, RESET_TTL = timedelta(hours=24), timedelta(minutes=30)
REAUTH_SECONDS = 5 * 60
LOGIN_PER_MIN_IP, LOGIN_PER_MIN_ALL = 30, 600
MAIL_PER_MIN_IP = 5


class Denied(Exception):
    """로그인 실패 — 계정 유무와 무관하게 같은 응답."""


class Wait(Exception):
    def __init__(self, seconds: float):
        self.seconds = max(1, int(seconds + 0.999))


class NeedCaptcha(Exception):
    pass


class BadInput(Exception):
    def __init__(self, code: str):
        self.code = code


class Forbidden(Exception):
    def __init__(self, code: str):
        self.code = code


def normalize(email: str) -> tuple[str, str]:
    """(저장용, 비교용). 앞뒤 공백 제거·도메인 소문자·비교는 전체 소문자. 점·+별칭은 그대로(SECURITY 1)."""
    e = (email or "").strip()
    if len(e) > 254 or e.count("@") != 1 or any(ch.isspace() for ch in e):
        raise BadInput("email")
    local, domain = e.split("@")
    if not local or "." not in domain.strip(".") or len(local) > 64:
        raise BadInput("email")
    e = f"{local}@{domain.lower()}"
    return e, e.lower()


def nickname_ok(nick: str) -> str:
    n = (nick or "").strip()
    if not 2 <= len(n) <= 16 or any(not ch.isprintable() for ch in n):
        raise BadInput("nickname")
    return n


def device_hash(device: str) -> bytes:
    return hashlib.sha256((device or "unknown")[:200].encode()).digest()


def _policy(pw: str, email: str | None, nick: str | None) -> None:
    reason = passwords.check(pw, email, nick)
    if reason:
        raise BadInput("password_" + reason)


# ---- 가입·인증 (검증 1) -------------------------------------------------------------------------


def signup(c, email: str, password: str, nickname: str, ip: str, lang: str = "en") -> None:
    """항상 같은 결과(None → 202 "메일을 확인하세요"). 계정이 있든 없든 해시를 한 번 계산해 시간도 맞춘다."""
    e, key = normalize(email)
    nick = nickname_ok(nickname)
    if not limits.budget(c, f"mail:ip:{ip}", MAIL_PER_MIN_IP):
        raise Wait(60)
    _policy(password, e, nick)
    pw_hash = passwords.hash(password)
    row = c.execute(
        "SELECT id, verified_at FROM accounts WHERE email_key = %s AND deleted_at IS NULL", (key,)
    ).fetchone()
    if row and row["verified_at"]:
        mail.send(e, "already", "/forgot", lang)
        return
    if row is None:
        try:
            with c.transaction():
                row = c.execute(
                    "INSERT INTO accounts (email, email_key, nickname, pw_hash) VALUES (%s, %s, %s, %s) RETURNING id",
                    (e, key, nick, pw_hash),
                ).fetchone()
        except errors.UniqueViolation:  # 같은 주소 동시 가입 — 먼저 만든 쪽에 인증 메일만
            row = c.execute("SELECT id FROM accounts WHERE email_key = %s AND deleted_at IS NULL", (key,)).fetchone()
    raw = tokens.issue(c, row["id"], "verify", VERIFY_TTL)
    mail.send(e, "verify", f"/verify?token={raw}", lang)


def verify(c, raw: str, password: str) -> None:
    """인증 링크 소비. 주소 주인이 비밀번호를 이 자리에서 다시 정한다 → 남이 먼저 가입해 둔(선점) 계정이어도
    선점자의 비밀번호·외부 로그인·MFA·복구 코드·세션·토큰을 모두 지운 뒤에만 활성화된다(같은 트랜잭션)."""
    t = tokens.consume(c, raw, "verify")
    if t is None:
        raise BadInput("token")
    a = c.execute("SELECT email, nickname FROM accounts WHERE id = %s", (t["account_id"],)).fetchone()
    _policy(password, a["email"], a["nickname"])
    aid = t["account_id"]
    c.execute("DELETE FROM identities WHERE account_id = %s", (aid,))
    c.execute("DELETE FROM recovery_codes WHERE account_id = %s", (aid,))
    c.execute("DELETE FROM known_devices WHERE account_id = %s", (aid,))
    c.execute("UPDATE auth_tokens SET expires_at = now() WHERE account_id = %s AND used_at IS NULL", (aid,))
    sessions.revoke_all(c, aid)
    c.execute(
        """UPDATE accounts SET pw_hash = %s, mfa_secret = NULL, mfa_enabled = false, mfa_last_step = NULL,
           verified_at = now() WHERE id = %s""",
        (passwords.hash(password), aid),
    )


def purge_unverified(c) -> int:
    """24시간 안에 인증하지 않은 가입은 지운다 → 주소 주인이 언제든 다시 가입할 수 있다."""
    return c.execute(
        "DELETE FROM accounts WHERE verified_at IS NULL AND created_at < now() - interval '24 hours'"
        " AND NOT EXISTS (SELECT 1 FROM identities i WHERE i.account_id = accounts.id)"
    ).rowcount


def resend_verify(c, email: str, ip: str, lang: str = "en") -> None:
    e, key = normalize(email)
    if not limits.budget(c, f"mail:ip:{ip}", MAIL_PER_MIN_IP):
        raise Wait(60)
    row = c.execute(
        "SELECT id FROM accounts WHERE email_key = %s AND deleted_at IS NULL AND verified_at IS NULL", (key,)
    ).fetchone()
    if row:
        mail.send(e, "verify", f"/verify?token={tokens.issue(c, row['id'], 'verify', VERIFY_TTL)}", lang)


# ---- 로그인 (검증 4) ----------------------------------------------------------------------------


def _gate(c, keys: list[str], ip: str, captcha: str | None, captcha_capable: bool) -> None:
    w = max(limits.wait(c, k) for k in keys)
    if w > 0:
        raise Wait(w)
    if not limits.budget(c, f"login:ip:{ip}", LOGIN_PER_MIN_IP) or not limits.budget(c, "login:all", LOGIN_PER_MIN_ALL):
        raise Wait(60)
    # 앱에는 Turnstile이 없다 → 앱 요청은 사람 확인 대신 위의 IP 지연(최대 15분)만. ponytail: 앱 출시 전 앱용 확인(Play Integrity 등) 추가
    if captcha_capable and limits.needs_captcha(c, ip) and not limits.captcha_ok(captcha, ip):
        raise NeedCaptcha


def login(
    c,
    email: str,
    password: str,
    ip: str,
    device: str,
    captcha: str | None = None,
    lang: str = "en",
    captcha_capable: bool = True,
) -> dict:
    """성공: {"access", "refresh", "mfa_required", "verified"}. 실패는 Denied(계정 유무와 같은 응답)."""
    try:
        _, key = normalize(email)
    except BadInput:
        key = "invalid"
    _gate(c, [f"acct:{key}", f"ip:{ip}"], ip, captcha, captcha_capable)
    row = c.execute(
        """SELECT id, email, pw_hash, verified_at, mfa_enabled FROM accounts
           WHERE email_key = %s AND deleted_at IS NULL AND locked_at IS NULL""",
        (key,),
    ).fetchone()
    ok, new_hash = passwords.verify(row["pw_hash"] if row else None, password)
    if not ok:
        limits.fail(c, f"acct:{key}")
        limits.fail(c, f"ip:{ip}")
        raise Denied
    limits.clear(c, f"acct:{key}")
    if new_hash:
        c.execute("UPDATE accounts SET pw_hash = %s WHERE id = %s", (new_hash, row["id"]))
    if not row["verified_at"]:
        return {"verified": False}
    return _open_session(c, row, device, ip, lang)


def _open_session(c, row: dict, device: str, ip: str, lang: str) -> dict:
    """새 기기면 알림 메일(검증 6). MFA가 켜져 있으면 MFA 전 세션(정해진 API만 허용)."""
    seen = c.execute(
        "INSERT INTO known_devices VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING 1",
        (row["id"], device_hash(device)),
    ).fetchone()
    first = c.execute("SELECT count(*) AS n FROM known_devices WHERE account_id = %s", (row["id"],)).fetchone()["n"]
    if seen and first > 1 and row["email"]:
        mail.send(row["email"], "new_device", tokens.protect_path(c, row["id"]), lang)
    access, refresh = sessions.create(c, row["id"], mfa_passed=not row["mfa_enabled"], device=device, ip=ip)
    return {"access": access, "refresh": refresh, "mfa_required": bool(row["mfa_enabled"]), "verified": True}


# ---- 재설정·변경 (검증 5) -----------------------------------------------------------------------


def reset_request(c, email: str, ip: str, lang: str = "en") -> None:
    """항상 같은 응답. 인증된 계정만 30분 토큰 메일. 링크 원점은 고정(Host 머리글 안 씀)."""
    try:
        e, key = normalize(email)
    except BadInput:
        return
    if not limits.budget(c, f"mail:ip:{ip}", MAIL_PER_MIN_IP):
        raise Wait(60)
    row = c.execute(
        "SELECT id, email FROM accounts WHERE email_key = %s AND deleted_at IS NULL AND verified_at IS NOT NULL",
        (key,),
    ).fetchone()
    if row:
        mail.send(row["email"], "reset", f"/reset?token={tokens.issue(c, row['id'], 'reset', RESET_TTL)}", lang)


def reset(c, raw: str, password: str, lang: str = "en") -> None:
    """비밀번호 교체 → 모든 세션 폐기·알림. 자동 로그인 없음, MFA는 그대로."""
    t = tokens.consume(c, raw, "reset")
    if t is None:
        raise BadInput("token")
    a = c.execute("SELECT email, nickname FROM accounts WHERE id = %s", (t["account_id"],)).fetchone()
    _policy(password, a["email"], a["nickname"])
    c.execute("UPDATE accounts SET pw_hash = %s WHERE id = %s", (passwords.hash(password), t["account_id"]))
    sessions.revoke_all(c, t["account_id"])
    mail.send(a["email"], "password_changed", tokens.protect_path(c, t["account_id"]), lang)


def require_recent(s: dict) -> None:
    """민감 작업: 5분 안에 실제로 다시 인증했고, MFA가 켜져 있으면 통과한 세션만."""
    if s["reauth_age"] > REAUTH_SECONDS:
        raise Forbidden("reauth")
    if s["mfa_enabled"] and not s["mfa_passed"]:
        raise Forbidden("mfa")


def reauth(c, s: dict, password: str) -> None:
    key = f"reauth:{s['account_id']}"
    if limits.wait(c, key) > 0:
        raise Wait(limits.wait(c, key))
    row = c.execute("SELECT pw_hash FROM accounts WHERE id = %s", (s["account_id"],)).fetchone()
    ok, _ = passwords.verify(row["pw_hash"], password)
    if not ok:
        limits.fail(c, key)
        raise Denied
    limits.clear(c, key)
    sessions.reauthed(c, s["sid"])


def change_password(c, s: dict, password: str, device: str, ip: str, lang: str = "en") -> dict:
    """로그인 중 변경: 최근 인증 + MFA. 다른 기기는 모두 로그아웃, 이 기기는 새 세션."""
    require_recent(s)
    a = c.execute("SELECT id, email, nickname, mfa_enabled FROM accounts WHERE id = %s", (s["account_id"],)).fetchone()
    _policy(password, a["email"], a["nickname"])
    c.execute("UPDATE accounts SET pw_hash = %s WHERE id = %s", (passwords.hash(password), a["id"]))
    sessions.revoke_all(c, a["id"])
    if a["email"]:
        mail.send(a["email"], "password_changed", tokens.protect_path(c, a["id"]), lang)
    access, refresh = sessions.create(c, a["id"], mfa_passed=True, device=device, ip=ip)
    return {"access": access, "refresh": refresh, "mfa_required": False, "verified": True}


# ---- 주소 변경·보호 (검증 6) --------------------------------------------------------------------
EMAIL_TTL = timedelta(hours=24)


def change_email(c, s: dict, email: str, lang: str = "en") -> None:
    """최근 재인증 + MFA 뒤, 새 주소로 확인 링크. 이미 쓰이는 주소여도 같은 응답(아무것도 안 보냄)."""
    require_recent(s)
    e, key = normalize(email)
    if c.execute("SELECT 1 FROM accounts WHERE email_key = %s AND deleted_at IS NULL", (key,)).fetchone():
        return
    raw = tokens.issue(c, s["account_id"], "email_confirm", EMAIL_TTL, target=e)
    mail.send(e, "email_confirm", f"/email?token={raw}", lang)


def confirm_email(c, raw: str, lang: str = "en") -> None:
    """새 주소 확인 → 교체. 인증 버전을 올려 남은 링크(옛 주소로 간 재설정 등)를 무효화하고,
    옛 주소엔 보호 링크를 보낸다(로그인·복원 권한 없음)."""
    t = tokens.consume(c, raw, "email_confirm")
    if t is None:
        raise BadInput("token")
    old = c.execute("SELECT email FROM accounts WHERE id = %s", (t["account_id"],)).fetchone()["email"]
    try:
        with c.transaction():
            c.execute(
                """UPDATE accounts SET email = %s, email_key = %s, auth_version = auth_version + 1,
                   verified_at = coalesce(verified_at, now()) WHERE id = %s""",
                (t["target"], t["target"].lower(), t["account_id"]),
            )
    except errors.UniqueViolation:
        raise BadInput("email_taken") from None
    if old:
        mail.send(old, "email_changed", tokens.protect_path(c, t["account_id"]), lang)


def protect(c, raw: str) -> None:
    """'내가 아니에요' — 모든 세션을 끊고 계정을 잠근다. 풀기는 운영자 확인(별도 복구 절차)."""
    t = tokens.consume(c, raw, "protect")
    if t is None:
        raise BadInput("token")
    sessions.revoke_all(c, t["account_id"])
    c.execute("UPDATE accounts SET locked_at = now() WHERE id = %s", (t["account_id"],))


# ---- 탈퇴 (검증 8) ------------------------------------------------------------------------------


def delete_account(c, s: dict) -> None:
    """최근 재인증(비밀번호 또는 구글) + MFA 뒤. 삭제 상태를 먼저 남겨 접근을 막고, 개인정보는 바로 지운다.
    삭제 이력(deletion_log)은 최소 식별자만 — 백업 복원 뒤 purge_deleted가 다시 적용한다."""
    require_recent(s)
    aid = s["account_id"]
    c.execute("UPDATE accounts SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (aid,))
    c.execute(
        "INSERT INTO deletion_log (account_ref, account_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (hashlib.sha256(f"acct:{aid}".encode()).digest(), aid),
    )
    sessions.revoke_all(c, aid)
    _purge(c, aid)


def _purge(c, aid: int) -> None:
    c.execute("DELETE FROM identities WHERE account_id = %s", (aid,))
    c.execute("DELETE FROM recovery_codes WHERE account_id = %s", (aid,))
    c.execute("DELETE FROM known_devices WHERE account_id = %s", (aid,))
    c.execute("DELETE FROM auth_tokens WHERE account_id = %s", (aid,))
    c.execute("DELETE FROM sessions WHERE account_id = %s", (aid,))
    for table in ("wallets", "ledger", "daily"):  # 화폐 기록(잔고·증감 시각·일일 활동)도 파기 — 결제를 붙이면 보관 의무를 다시 본다
        c.execute(f"DELETE FROM {table} WHERE account_id = %s", (aid,))
    c.execute(
        """UPDATE accounts SET email = NULL, email_key = NULL, nickname = '', pw_hash = NULL, mfa_secret = NULL,
           mfa_enabled = false, deleted_at = coalesce(deleted_at, now()) WHERE id = %s""",
        (aid,),
    )
    c.execute("UPDATE deletion_log SET purged_at = now() WHERE account_id = %s", (aid,))


def purge_deleted(c) -> int:
    """삭제 이력에 있는데 개인정보가 남은 계정(백업 복원 등)을 다시 지운다. 여러 번 돌려도 같다."""
    rows = c.execute(
        """SELECT l.account_id FROM deletion_log l JOIN accounts a ON a.id = l.account_id
           WHERE a.deleted_at IS NULL OR a.email IS NOT NULL OR a.pw_hash IS NOT NULL OR a.nickname <> ''
              OR EXISTS (SELECT 1 FROM identities i WHERE i.account_id = a.id)
              OR EXISTS (SELECT 1 FROM sessions x WHERE x.account_id = a.id)
              OR EXISTS (SELECT 1 FROM wallets w WHERE w.account_id = a.id)"""
    ).fetchall()
    for r in rows:
        sessions.revoke_all(c, r["account_id"])
        _purge(c, r["account_id"])
    return len(rows)
