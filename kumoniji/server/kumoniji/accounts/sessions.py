"""세션·액세스·리프레시(SECURITY.md 2절 '토큰 검증·회전'·'세션 영속성', 검증 11·12).

- 액세스: JWT HS256 15분. 서명·알고리즘·iss·aud·exp·typ를 검사하고, 매 요청 DB에서 세션 폐기·계정 인증 버전을 확인.
- 리프레시: 불투명 32바이트, DB엔 SHA-256만. 유휴 30일 만료, 절대 만료 없음(ADR-0017). 쓸 때마다 원자적으로 회전.
- 이미 회전된 리프레시가 다시 오면 탈취로 보고 그 계정의 모든 세션을 폐기한다.
"""

import os
import secrets
import time
import uuid

import jwt

from . import mail
from .tokens import digest, protect_path

ACCESS_TTL = 15 * 60
RACE_GRACE = 30
IDLE = "30 days"
ISS = AUD = "kumoniji"


class Reused(Exception):
    """이미 회전된 리프레시 재사용 — 전 세션 폐기됨."""


class Raced(Exception):
    """방금(RACE_GRACE초 안) 같은 세션이 회전함 — 웹의 다른 탭이 먼저 갱신한 것. 쿠키는 탭끼리 공유되므로
    이 탭은 이미 새 쿠키를 갖고 있다 → 폐기하지 않고 다시 시도하게 한다. 이 응답엔 새 토큰이 없어 탈취자는 얻는 게 없다."""


def _key() -> str:
    k = os.environ.get("KUMONIJI_JWT_SECRET", "")
    if len(k) < 32:
        raise RuntimeError("KUMONIJI_JWT_SECRET이 없거나 짧음")
    return k


def access_token(account_id: int, sid: str, version: int) -> str:
    now = int(time.time())
    claims = {"sub": str(account_id), "sid": sid, "ver": version, "typ": "access"}
    return jwt.encode(claims | {"iss": ISS, "aud": AUD, "iat": now, "exp": now + ACCESS_TTL}, _key(), "HS256")


def create(c, account_id: int, *, mfa_passed: bool, device: str = "", ip: str = "") -> tuple[str, str]:
    """(액세스, 리프레시). reauth_at은 실제 인증(비밀번호·구글·MFA) 시각 — 갱신으로 늘지 않는다."""
    sid, raw = str(uuid.uuid4()), secrets.token_urlsafe(32)
    v = c.execute(
        """INSERT INTO sessions (id, account_id, refresh_hash, device, ip, reauth_at, mfa_passed)
           VALUES (%s, %s, %s, %s, %s, now(), %s)
           RETURNING (SELECT auth_version FROM accounts WHERE id = %s) AS ver""",
        (sid, account_id, digest(raw), device[:200], ip[:64], mfa_passed, account_id),
    ).fetchone()["ver"]
    return access_token(account_id, sid, v), raw


def refresh(c, raw: str) -> tuple[str, str] | None:
    """회전. 반환 (새 액세스, 새 리프레시) 또는 None(만료·폐기·모름). 재사용이면 Reused."""
    if not raw or len(raw) > 128:
        return None
    new = secrets.token_urlsafe(32)
    row = c.execute(
        f"""UPDATE sessions s SET refresh_hash = %s, last_used_at = now()
            FROM accounts a
            WHERE s.refresh_hash = %s AND s.revoked_at IS NULL AND s.last_used_at > now() - interval '{IDLE}'
              AND a.id = s.account_id AND a.deleted_at IS NULL AND a.locked_at IS NULL
            RETURNING s.id, s.account_id, a.auth_version""",
        (digest(new), digest(raw)),
    ).fetchone()
    if row:
        c.execute("INSERT INTO spent_refresh (hash, session_id) VALUES (%s, %s)", (digest(raw), row["id"]))
        return access_token(row["account_id"], str(row["id"]), row["auth_version"]), new
    old = c.execute(
        """SELECT s.account_id, p.spent_at > now() - %s * interval '1 second' AS just_now
           FROM spent_refresh p JOIN sessions s ON s.id = p.session_id
           WHERE p.hash = %s AND s.revoked_at IS NULL""",
        (RACE_GRACE, digest(raw)),
    ).fetchone()
    if old and old["just_now"]:
        raise Raced
    if old:
        revoke_all(c, old["account_id"])
        _notify(c, old["account_id"], "security")
        raise Reused
    return None


def decode(token: str | None) -> dict | None:
    """액세스 토큰의 서명·만료·발급자 확인(DB 없이). 쓸 수 없으면 None."""
    if not token or len(token) > 2048:
        return None
    try:
        claims = jwt.decode(
            token, _key(), algorithms=["HS256"], audience=AUD, issuer=ISS, options={"require": ["exp", "sub", "sid"]}
        )
    except jwt.PyJWTError:
        return None
    return claims if claims.get("typ") == "access" else None


def current(c, token: str | None) -> dict | None:
    """액세스 토큰 → {"account_id", "sid", "mfa_passed", "reauth_age", "verified"} 또는 None."""
    if (claims := decode(token)) is None:
        return None
    return live(c, claims["sid"], int(claims["sub"]), claims.get("ver"), idle_ok=True)


def live(c, sid: str, account_id: int, ver, *, idle_ok: bool = False) -> dict | None:
    """세션이 아직 살아 있나(폐기·비밀번호 변경·탈퇴·잠금 아님). 토큰 만료와 무관 — 오래 열린 소켓의 재확인용.
    idle_ok=False면 리프레시처럼 30일 유휴 만료도 적용한다(HTTP 액세스 토큰은 15분이라 따로 볼 필요 없음)."""
    idle = "" if idle_ok else f"AND s.last_used_at > now() - interval '{IDLE}'"
    return c.execute(
        f"""SELECT a.id AS account_id, s.id::text AS sid, s.mfa_passed, a.verified_at IS NOT NULL AS verified,
                  a.mfa_enabled, extract(epoch FROM now() - s.reauth_at) AS reauth_age, a.auth_version AS ver
           FROM sessions s JOIN accounts a ON a.id = s.account_id
           WHERE s.id = %s AND a.id = %s AND s.revoked_at IS NULL AND a.auth_version = %s
             AND a.deleted_at IS NULL AND a.locked_at IS NULL {idle}""",
        (sid, account_id, ver),
    ).fetchone()


def reauthed(c, sid: str, *, mfa: bool = False) -> None:
    """방금 비밀번호·구글(·MFA)로 다시 인증함 → 최근 인증 시각 갱신."""
    c.execute("UPDATE sessions SET reauth_at = now(), mfa_passed = mfa_passed OR %s WHERE id = %s", (mfa, sid))


def revoke(c, account_id: int, sid: str) -> None:
    c.execute("UPDATE sessions SET revoked_at = now() WHERE id = %s AND account_id = %s", (sid, account_id))


def revoke_all(c, account_id: int) -> None:
    """모든 세션 폐기 + 인증 버전 증가(발급된 액세스·미소비 인증 토큰도 무효)."""
    c.execute("UPDATE sessions SET revoked_at = now() WHERE account_id = %s AND revoked_at IS NULL", (account_id,))
    c.execute("UPDATE accounts SET auth_version = auth_version + 1 WHERE id = %s", (account_id,))


def listing(c, account_id: int) -> list[dict]:
    return c.execute(
        """SELECT id::text AS id, device, created_at, last_used_at FROM sessions
           WHERE account_id = %s AND revoked_at IS NULL ORDER BY last_used_at DESC""",
        (account_id,),
    ).fetchall()


def _notify(c, account_id: int, kind: str) -> None:
    r = c.execute("SELECT email FROM accounts WHERE id = %s", (account_id,)).fetchone()
    if r and r["email"]:
        mail.send(r["email"], kind, protect_path(c, account_id))


def sweep(c) -> None:
    """30일 지난 회전 이력 정리(주기 작업)."""
    c.execute(f"DELETE FROM spent_refresh WHERE spent_at < now() - interval '{IDLE}'")
