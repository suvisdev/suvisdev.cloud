"""1회용 인증 토큰(가입 인증·재설정·주소 변경·옛 주소 보호) — SECURITY.md 1절 '인증 토큰', 검증 3."""

import hashlib
import secrets
from datetime import timedelta


def digest(raw: str) -> bytes:
    return hashlib.sha256(raw.encode()).digest()


def issue(c, account_id: int, purpose: str, ttl: timedelta, target: str | None = None) -> str:
    """32바이트 난수 토큰. DB엔 해시만. 같은 계정·목적의 이전 토큰은 무효(만료 처리).
    단 보호 링크는 예외 — 탈취자가 새 알림을 일으켜 주인이 받은 링크를 죽이지 못하게 모두 살려 둔다."""
    raw = secrets.token_urlsafe(32)
    if purpose != "protect":
        # 같은 계정의 동시 발급을 줄 세운다 — 안 그러면 서로의 미커밋 토큰을 못 보고 둘 다 유효로 남는다
        c.execute("SELECT 1 FROM accounts WHERE id = %s FOR UPDATE", (account_id,))
        c.execute(
            "UPDATE auth_tokens SET expires_at = now() WHERE account_id = %s AND purpose = %s AND used_at IS NULL",
            (account_id, purpose),
        )
    c.execute(
        """INSERT INTO auth_tokens (hash, account_id, purpose, target, version, expires_at)
           SELECT %s, id, %s, %s, auth_version, now() + %s FROM accounts WHERE id = %s""",
        (digest(raw), purpose, target, ttl, account_id),
    )
    return raw


def consume(c, raw: str, purpose: str) -> dict | None:
    """원자적 1회 소비. 목적·만료·계정 인증 버전(비밀번호·주소가 바뀌면 오른다)이 맞아야 한다.
    보호 링크만 버전을 보지 않는다 — 탈취자가 비밀번호를 바꿔도 주인의 신고 링크는 살아 있어야 한다.
    반환: {"account_id", "target"} 또는 None."""
    if not raw or len(raw) > 128:
        return None
    return c.execute(
        """UPDATE auth_tokens t SET used_at = now()
           FROM accounts a
           WHERE t.hash = %s AND t.purpose = %s AND t.used_at IS NULL AND t.expires_at > now()
             AND a.id = t.account_id AND (t.version = a.auth_version OR t.purpose = 'protect') AND a.deleted_at IS NULL
           RETURNING t.account_id, t.target""",
        (digest(raw), purpose),
    ).fetchone()


def peek(c, raw: str, purpose: str) -> bool:
    """소비하지 않고 유효한지만(링크 GET 화면용 — 메일 스캐너가 열어도 토큰이 안 닳게)."""
    if not raw or len(raw) > 128:
        return False
    return (
        c.execute(
            """SELECT 1 FROM auth_tokens t JOIN accounts a ON a.id = t.account_id
               WHERE t.hash = %s AND t.purpose = %s AND t.used_at IS NULL AND t.expires_at > now()
                 AND (t.version = a.auth_version OR t.purpose = 'protect') AND a.deleted_at IS NULL""",
            (digest(raw), purpose),
        ).fetchone()
        is not None
    )


PROTECT_TTL = timedelta(days=7)


def protect_path(c, account_id: int) -> str:
    """알림 메일의 '내가 아니에요' 링크(7일, 1회). 로그인·주소 복원 권한은 없다 — 잠그기만 한다."""
    return f"/protect?token={issue(c, account_id, 'protect', PROTECT_TTL)}"
