"""2단계 인증(TOTP) — SECURITY.md 1절 'MFA', 검증 7·8.

- 비밀은 Fernet(KUMONIJI_TOTP_KEY)으로 암호화해 저장. 켜기 전 코드 한 번을 맞혀야 켜진다.
- 앞뒤 한 칸(±30초)까지 받고, 같은 칸 이하 코드는 다시 받지 않는다(mfa_last_step을 원자적으로 올림).
- 복구 코드 10개, SHA-256만 저장, 한 번 쓰면 끝. 켜기·끄기·재발급은 최근 재인증 + 알림 메일.
"""

import hashlib
import hmac
import os
import secrets
import time

import pyotp
from cryptography.fernet import Fernet

from . import limits, mail, sessions, tokens
from .service import Denied, Forbidden, Wait, require_recent

ISSUER = "Kumoniji"
CODES = 10


def _fernet() -> Fernet:
    return Fernet(os.environ["KUMONIJI_TOTP_KEY"].encode())


def _norm(code: str) -> str:
    return "".join(ch for ch in (code or "") if ch.isalnum()).lower()[:32]


def setup(c, s: dict) -> dict:
    """새 비밀을 만들어 둔다(아직 꺼진 상태). 앱이 QR로 보여 준다."""
    require_recent(s)
    # 행을 잠그고 탈퇴 여부를 다시 본다 — 세션 확인 뒤 탈퇴가 먼저 커밋됐으면 지운 계정에 비밀값을 새로 쓰지 않게(약관 리뷰 9차)
    a = c.execute(
        "SELECT email, nickname, mfa_enabled FROM accounts WHERE id = %s AND deleted_at IS NULL FOR UPDATE",
        (s["account_id"],),
    ).fetchone()
    if a is None:
        raise Denied
    if a["mfa_enabled"]:
        raise Forbidden("mfa_on")
    secret = pyotp.random_base32()
    c.execute(
        "UPDATE accounts SET mfa_secret = %s, mfa_last_step = NULL WHERE id = %s",
        (_fernet().encrypt(secret.encode()), s["account_id"]),
    )
    uri = pyotp.TOTP(secret).provisioning_uri(name=a["email"] or a["nickname"], issuer_name=ISSUER)
    return {"secret": secret, "uri": uri}


def _totp_ok(c, account_id: int, code: str) -> bool:
    row = c.execute("SELECT mfa_secret FROM accounts WHERE id = %s", (account_id,)).fetchone()
    if not row or not row["mfa_secret"] or len(code) != 6 or not code.isdigit():
        return False
    totp = pyotp.TOTP(_fernet().decrypt(bytes(row["mfa_secret"])).decode())
    now = int(time.time()) // 30
    for step in (now - 1, now, now + 1):
        if hmac.compare_digest(totp.at(step * 30).encode(), code.encode()):  # 바이트로 — 비ASCII 입력에 TypeError 없이(55차)
            return bool(
                c.execute(
                    """UPDATE accounts SET mfa_last_step = %s
                       WHERE id = %s AND (mfa_last_step IS NULL OR mfa_last_step < %s) RETURNING 1""",
                    (step, account_id, step),
                ).fetchone()
            )
    return False


def _recovery_ok(c, account_id: int, code: str) -> bool:
    h = hashlib.sha256(code.encode()).digest()
    return bool(
        c.execute(
            """UPDATE recovery_codes SET used_at = now()
               WHERE account_id = %s AND hash = %s AND used_at IS NULL RETURNING 1""",
            (account_id, h),
        ).fetchone()
    )


def _check(c, account_id: int, code: str, recovery: bool) -> None:
    """틀리면 Denied(실패 기록), 지연 중이면 Wait."""
    key = f"mfa:{account_id}"
    w = limits.wait(c, key)
    if w > 0:
        raise Wait(w)
    code = _norm(code)
    if _totp_ok(c, account_id, code) or (recovery and _recovery_ok(c, account_id, code)):
        limits.clear(c, key)
        return
    limits.fail(c, key)
    raise Denied


def _new_codes(c, account_id: int) -> list[str]:
    c.execute("DELETE FROM recovery_codes WHERE account_id = %s", (account_id,))
    codes = [secrets.token_hex(5) for _ in range(CODES)]
    for code in codes:
        c.execute(
            "INSERT INTO recovery_codes (account_id, hash) VALUES (%s, %s)",
            (account_id, hashlib.sha256(code.encode()).digest()),
        )
    return codes


def _notify(c, account_id: int, lang: str) -> None:
    r = c.execute("SELECT email FROM accounts WHERE id = %s", (account_id,)).fetchone()
    if r and r["email"]:
        mail.send(r["email"], "security", tokens.protect_path(c, account_id), lang)


def enable(c, s: dict, code: str, lang: str = "en") -> list[str]:
    """설정 직후 코드를 맞히면 켠다. 다른 기기는 로그아웃, 이 세션은 MFA 통과로 남긴다. 복구 코드를 한 번만 보여 준다."""
    require_recent(s)
    _check(c, s["account_id"], code, recovery=False)
    c.execute("UPDATE accounts SET mfa_enabled = true WHERE id = %s AND mfa_secret IS NOT NULL", (s["account_id"],))
    c.execute(
        "UPDATE sessions SET revoked_at = now() WHERE account_id = %s AND id <> %s AND revoked_at IS NULL",
        (s["account_id"], s["sid"]),
    )
    sessions.reauthed(c, s["sid"], mfa=True)
    _notify(c, s["account_id"], lang)
    return _new_codes(c, s["account_id"])


def verify(c, s: dict, code: str) -> None:
    """MFA 전 세션 → 통과. TOTP 또는 복구 코드."""
    _check(c, s["account_id"], code, recovery=True)
    sessions.reauthed(c, s["sid"], mfa=True)


def disable(c, s: dict, code: str, lang: str = "en") -> None:
    require_recent(s)
    _check(c, s["account_id"], code, recovery=True)
    c.execute(
        "UPDATE accounts SET mfa_enabled = false, mfa_secret = NULL, mfa_last_step = NULL WHERE id = %s",
        (s["account_id"],),
    )
    c.execute("DELETE FROM recovery_codes WHERE account_id = %s", (s["account_id"],))
    _notify(c, s["account_id"], lang)


def regenerate(c, s: dict, lang: str = "en") -> list[str]:
    require_recent(s)
    _notify(c, s["account_id"], lang)
    return _new_codes(c, s["account_id"])
