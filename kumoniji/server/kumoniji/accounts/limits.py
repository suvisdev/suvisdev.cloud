"""시도 제한·CAPTCHA(SECURITY.md 1절 '열거·대입 방지', 검증 4). 상태는 Postgres에만(SECURITY 12: Redis 단독 금지).

- 실패 지연: 같은 키로 5번 실패한 뒤부터 2^(n-5)초 기다려야 다음 시도. 최대 15분, 영구 잠금 없음.
- 예산: 키마다 분당 횟수 상한(IP별·전체) — 해시·메일 자원을 지킨다.
- CAPTCHA: 같은 IP가 10번 넘게 실패하면 Cloudflare Turnstile 토큰을 요구.
"""

import os

import httpx

FREE, MAX_WAIT, CAPTCHA_AFTER = 5, 900, 10
TURNSTILE = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def wait(c, key: str) -> float:
    """다음 시도까지 남은 초(0이면 바로 가능)."""
    r = c.execute(
        "SELECT greatest(0, extract(epoch FROM until - now())) AS s FROM attempts WHERE key = %s", (key,)
    ).fetchone()
    return float(r["s"]) if r and r["s"] is not None else 0.0


def fail(c, key: str) -> None:
    c.execute(
        """INSERT INTO attempts (key, fails, until) VALUES (%s, 1, NULL)
           ON CONFLICT (key) DO UPDATE SET
             fails = attempts.fails + 1, seen = now(),
             until = CASE WHEN attempts.fails + 1 >= %s
                          THEN now() + least(%s, power(2, attempts.fails + 1 - %s)) * interval '1 second' END""",
        (key, FREE, MAX_WAIT, FREE),
    )


def fails(c, key: str) -> int:
    r = c.execute("SELECT fails FROM attempts WHERE key = %s", (key,)).fetchone()
    return r["fails"] if r else 0


def clear(c, key: str) -> None:
    c.execute("DELETE FROM attempts WHERE key = %s", (key,))


def budget(c, key: str, per_minute: int) -> bool:
    """분당 횟수 안이면 True(그리고 한 번 셈)."""
    r = c.execute(
        """INSERT INTO attempts (key, fails, seen) VALUES (%s, 1, now())
           ON CONFLICT (key) DO UPDATE SET
             fails = CASE WHEN attempts.seen < now() - interval '1 minute' THEN 1 ELSE attempts.fails + 1 END,
             seen  = CASE WHEN attempts.seen < now() - interval '1 minute' THEN now() ELSE attempts.seen END
           RETURNING fails""",
        ("rate:" + key,),
    ).fetchone()
    return r["fails"] <= per_minute


def needs_captcha(c, ip: str) -> bool:
    return fails(c, "ip:" + ip) >= CAPTCHA_AFTER


def captcha_ok(token: str | None, ip: str, client: httpx.Client | None = None) -> bool:
    """Turnstile 서버 검증. 비밀 키가 없거나 검증 서버가 안 되면 통과시키지 않는다(실패 쪽으로 닫힘)."""
    secret = os.environ.get("KUMONIJI_TURNSTILE_SECRET", "")
    if not secret or not token or len(token) > 2048:
        return False
    try:
        r = (client or httpx).post(TURNSTILE, data={"secret": secret, "response": token, "remoteip": ip}, timeout=5)
        return bool(r.json().get("success"))
    except (httpx.HTTPError, ValueError):
        return False


def sweep(c) -> None:
    """하루 넘게 안 쓴 기록 정리(주기 작업)."""
    c.execute("DELETE FROM attempts WHERE seen < now() - interval '1 day' AND (until IS NULL OR until < now())")
