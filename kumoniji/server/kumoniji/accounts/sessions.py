"""세션·액세스·리프레시(SECURITY.md 2절 '토큰 검증·회전'·'세션 영속성', 검증 11·12).

- 액세스: JWT HS256 15분. 서명·알고리즘·iss·aud·exp·typ를 검사하고, 매 요청 DB에서 세션 폐기·계정 인증 버전을 확인.
- 리프레시: 불투명 32바이트, DB엔 SHA-256만. 유휴 30일 만료, 절대 만료 없음(ADR-0017). 쓸 때마다 원자적으로 회전.
- 이미 회전된 리프레시가 다시 오면 탈취로 보고 그 계정의 모든 세션을 폐기한다.
- 멱등 갱신: 새 리프레시는 옛 것에서 HMAC으로 파생한다. 응답을 못 받은 클라이언트(시간 초과로 끊음)가 같은 옛 토큰으로
  다시 오면, 그 새 토큰이 아직 안 쓰였고 REPLAY 안이며 회전한 요청과 같은 재시도 키(클라이언트 메모리에만 있는 무작위
  값)를 보냈으면 같은 새 토큰을 다시 준다 — 원본을 저장하지 않고도, 훔친 토큰엔 열리지 않게(앱 리뷰 30·48·49·50차).
"""

import base64
import hashlib
import hmac
import os
import secrets
import time
import uuid

import jwt

from . import mail
from .tokens import digest, protect_path

ACCESS_TTL = 15 * 60
RACE_GRACE = 30
# 응답을 못 받은 클라이언트가 다시 받을 수 있는 시간. 액세스 수명보다 길어야 한다 — 늦게 온 같은 응답이 이미 한 번 더
# 회전한 쿠키를 옛 것으로 덮으면, 그 액세스가 끝나는 15분 뒤에야 옛 토큰으로 갱신하러 온다(앱 리뷰 33차 ②)
REPLAY = ACCESS_TTL + 600
MAX_REPLAYS = 5  # 하루에 다시 받기를 이보다 많이 하면 탈취로 본다(마이그레이션 004 sessions.replays)
# 방금 회전된 토큰의 다시 받기(같은 브라우저 탭들의 동시 갱신)는 따로 센다 — 회전마다 탭 셋까지 겹쳐도 되게 넉넉히,
# 그래도 끝은 있게(훔친 쪽이 늘 30초 안에 따라붙어 한도를 피하지 못하게, 앱 리뷰 46차)
MAX_RACES = 2 * 86400 // ACCESS_TTL
CHAIN = 5  # 다시 받을 때 따라갈 회전 수(같은 브라우저의 탭 몇 개가 겹쳐 회전해도 되게)
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


def _next(raw: str) -> str:
    """옛 리프레시 → 새 리프레시(결정적). 키는 JWT 비밀에서 용도를 갈라 파생 — 비밀을 모르면 예측할 수 없다."""
    key = hashlib.sha256(b"kumoniji-refresh-chain:" + _key().encode()).digest()
    return base64.urlsafe_b64encode(hmac.digest(key, raw.encode(), "sha256")).rstrip(b"=").decode()


def retry_key(sid: str) -> str:
    """웹 재시도 키 — 세션에서 정해지는 값(비밀 없이는 계산 못 함). 무작위로 새로 만들면 같은 브라우저의 두 탭이
    동시에 서로 다른 키를 받아 늦은 쪽이 덮고, 다시 받기가 탈취로 판정된다(앱 리뷰 33·36차). 정해진 값이면 몇 번을
    동시에 심어도 같다."""
    key = hashlib.sha256(b"kumoniji-retry-key:" + _key().encode()).digest()
    return base64.urlsafe_b64encode(hmac.digest(key, sid.encode(), "sha256")).rstrip(b"=").decode()


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


def refresh(c, raw: str, lang: str = "en", retry: str = "", ip: str = "") -> tuple[str, str] | None:
    """회전. 반환 (새 액세스, 새 리프레시) 또는 None(만료·폐기·모름). 재사용이면 Reused, 웹의 동시 갱신이면 Raced.
    retry는 재시도 키."""
    if not raw or len(raw) > 128:
        return None
    new = _next(raw)
    row = c.execute(
        f"""UPDATE sessions s SET refresh_hash = %s, last_used_at = now()
            FROM accounts a
            WHERE s.refresh_hash = %s AND s.revoked_at IS NULL AND s.last_used_at > now() - interval '{IDLE}'
              AND a.id = s.account_id AND a.deleted_at IS NULL AND a.locked_at IS NULL
            RETURNING s.id, s.account_id, a.auth_version""",
        (digest(new), digest(raw)),
    ).fetchone()
    if row:
        c.execute(
            "INSERT INTO spent_refresh (hash, session_id, retry, ip) VALUES (%s, %s, %s, %s)",
            (digest(raw), row["id"], digest(retry) if retry else None, ip[:64]),
        )
        return access_token(row["account_id"], str(row["id"]), row["auth_version"]), new
    # 남는 틈(알고 둠, 11-26 사용자 결정 1번): 웹에서 갱신 요청(첫 회전이든 다시 받기든)이 날아가는 동안 다른 탭이
    # 다른 계정으로 로그인하면, 그 뒤 도착한 응답의 쿠키가 새 로그인을 덮는다. 서버는 요청이 떠난 뒤의 다른 탭 로그인을
    # 알 수 없다. 앱이 요청을 제한 시간(15초)에 끊어 이 틈을 '무한'에서 '15초 안'으로 줄였고, 같은 브라우저 안에서
    # 화면 계정이 바뀌는 것뿐(account_changed로 감지해 다시 읽음, 다른 사람에게 토큰이 가지 않음)이다(앱 리뷰 28·40·58차).
    # 응답을 못 받아 같은 키로 다시 옴 — 새 토큰이 아직 안 쓰였으면 같은 것을 다시 준다. 조건 확인과 갱신을 한 UPDATE로
    # (세션 행 잠금 아래 다시 확인) — 그사이 다른 탭이 한 번 더 회전했으면 걸리지 않는다(앱 리뷰 50차)
    # 같은 브라우저가 그 뒤로도 회전했으면(늦은 응답이 쿠키를 옛 토큰으로 되돌림) 사슬을 따라간다 — 지나는 토큰마다
    # 같은 키로·REPLAY 안에 쓰였어야 한다(앱 리뷰 34차). 새 토큰은 옛 것에서 파생되니 원본 없이도 다음을 안다.
    if retry and len(retry) <= 128:
        # 정상 경합인지는 처음 보낸 토큰이 방금 회전됐는지로 본다 — 사슬 끝의 토큰이 방금이어도 처음 토큰이 오래됐으면
        # 다시 받기로 센다(앱 리뷰 44차)
        # 계정 행을 먼저 잠근다 — 아래 UPDATE가 세션 행을 잠근 뒤 한도를 넘어 revoke_all이 계정 행을 잠그면, 계정 →
        # 세션 순으로 잠그는 비밀번호 변경과 엇갈려 교착한다(앱 리뷰 45차). 다시 받기는 드물어 늘 잠가도 싸다
        just = c.execute(
            # 같은 IP에서 온 것만 동시 갱신으로 본다 — 쿠키(리프레시+키)를 함께 훔친 사람이 회전마다 30초 안에 따라붙어도
            # 다른 IP면 다시 받기로 세어 하루 MAX_REPLAYS에서 걸린다(앱 리뷰 52차)
            # 폐기된 세션이면 동시 갱신(409)으로 답하지 않는다 — 아래 일반 경로가 401로 끝내 로그인 화면으로(화폐 재리뷰)
            """SELECT p.spent_at > now() - %s * interval '1 second' AND s.revoked_at IS NULL AS recent,
                      p.ip = %s AS same_ip, s.id::text AS sid
               FROM spent_refresh p JOIN sessions s ON s.id = p.session_id JOIN accounts a ON a.id = s.account_id
               WHERE p.hash = %s FOR UPDATE OF a""",
            (RACE_GRACE, ip[:64], digest(raw)),
        ).fetchone()
        fresh = bool(just and just["recent"] and just["same_ip"])
        # 웹의 동시 갱신에는 새 토큰을 다시 주지 않는다 — 탭은 쿠키를 함께 써서 먼저 회전한 탭의 응답이 이미 새 쿠키를
        # 심었으니 409 뒤 다시 보내면 된다. 다시 주면 쿠키 두 개를 함께 훔친 사람(같은 PC의 악성 프로그램이면 IP도 같다)이
        # 회전마다 30초 안에 따라붙어 하루 한도 아래로 며칠씩 쓴다(리뷰, 11-26 사용자 결정 3번). 응답을 잃은 탭은 30초가
        # 지나면 아래 다시 받기로 받는다. 앱은 재시도 키가 메모리에만 있어 그대로 다시 준다(응답 유실 복구)
        # 웹인지는 요청 헤더가 아니라 키로 본다 — 웹 키는 서버가 세션에서 만들어 쿠키로 심은 값(retry_key)이라, 훔친 쿠키를
        # 앱 경로(헤더)로 보내도 웹으로 걸린다(리뷰). 앱 키는 클라이언트가 만든 무작위 값이라 같을 수 없다
        # IP와 무관하게 — 다른 IP에서 훔친 쿠키 쌍으로 와도 30초 안이면 다시 주지 않는다(화폐 재리뷰). IP는 셈(경합·다시 받기)에만
        if just and just["recent"] and hmac.compare_digest(retry.encode(), retry_key(just["sid"]).encode()):
            raise Raced
        tok = raw
        for _ in range(CHAIN):
            nxt = _next(tok)
            row = c.execute(
                # 방금(RACE_GRACE 안) 회전된 토큰은 같은 브라우저 탭들의 동시 갱신 — 정상 경합이라 세지 않는다(앱 리뷰 41차)
                f"""UPDATE sessions s SET last_used_at = now(),
                        replays = CASE WHEN s.replayed_at::date = now()::date THEN s.replays ELSE 0 END
                                  + CASE WHEN %s OR p.replayed THEN 0 ELSE 1 END,
                        races = CASE WHEN s.replayed_at::date = now()::date THEN s.races ELSE 0 END
                                + CASE WHEN %s AND NOT p.raced THEN 1 ELSE 0 END,
                        replayed_at = now()
                    FROM spent_refresh p, accounts a
                    WHERE p.hash = %s AND p.retry = %s AND p.spent_at > now() - %s * interval '1 second'
                      AND s.id = p.session_id AND s.refresh_hash = %s AND s.revoked_at IS NULL
                      AND s.last_used_at > now() - interval '{IDLE}'
                      AND a.id = s.account_id AND a.deleted_at IS NULL AND a.locked_at IS NULL
                    RETURNING s.id, s.account_id, a.auth_version, s.replays, s.races""",
                (fresh, fresh, digest(tok), digest(retry), REPLAY, digest(nxt)),
            ).fetchone()
            if row and (row["replays"] > MAX_REPLAYS or row["races"] > MAX_RACES):
                # 정상 다시 받기(응답 유실)는 드물다 — 하루에 이만큼 넘으면 쿠키(리프레시+키)를 함께 훔친 사람이 주인과
                # 번갈아 다시 받는 것으로 본다(앱 리뷰 40차). 폐기를 커밋해야 하므로 Reused로(부르는 쪽이 트랜잭션 안에서 잡음)
                revoke_all(c, row["account_id"])
                _notify(c, row["account_id"], "security", lang)
                raise Reused
            if row:
                # 같은 토큰의 다시 받기는 한 번만 센다 — 응답 하나를 잃고 탭 여럿이 같은 쿠키로 복구해도 한도를 넘지 않게.
                # 훔친 사람은 회전마다 새 토큰을 다시 받아야 하니 여전히 회전마다 하나씩 세어진다(앱 리뷰 56차). 계정 행을
                # 잠근 채라 겹친 탭은 차례로 온다
                # 동시 갱신(경합)도 같다 — 탭 4개가 함께 갱신해도 회전당 한 번(앱 리뷰 57차)
                # 표시는 둘을 따로 — 동시 갱신 표시가 다른 IP 다시 받기의 셈을 막지 않게(58차)
                col = "raced" if fresh else "replayed"
                c.execute(f"UPDATE spent_refresh SET {col} = true WHERE hash = %s", (digest(tok),))
                return access_token(row["account_id"], str(row["id"]), row["auth_version"]), nxt
            mine = c.execute(
                """SELECT count(*) AS n FROM spent_refresh
                   WHERE hash IN (%s, %s) AND retry = %s AND spent_at > now() - %s * interval '1 second'""",
                (digest(tok), digest(nxt), digest(retry), REPLAY),
            ).fetchone()
            if mine["n"] < 2:
                break
            tok = nxt
    old = c.execute(
        """SELECT s.account_id, s.id::text AS sid, p.spent_at > now() - %s * interval '1 second' AS just_now,
                  p.retry IS NOT NULL AND p.retry = %s AS mine
           FROM spent_refresh p JOIN sessions s ON s.id = p.session_id
           WHERE p.hash = %s AND s.revoked_at IS NULL""",
        (RACE_GRACE, digest(retry), digest(raw)),
    ).fetchone()
    # 방금 회전된 토큰 — 같은 브라우저의 다른 탭이 이미 더 새 쿠키를 받았을 수 있다. 쿠키를 지우지 않고 409로(같은 키
    # 여도: 지우면 그 탭의 최신 쿠키까지 날아간다, 앱 리뷰 61차)
    if old and old["just_now"]:
        raise Raced
    # 회전한 바로 그 클라이언트(같은 재시도 키)인데 다시 줄 수 없음 — 탈취로 보지 않아 다른 기기 세션은 둔다(앱 리뷰 57차).
    # 이 세션은 끊는다: 쿠키와 재시도 키가 함께 새어 남이 먼저 갱신했다면(추적 한도 CHAIN을 넘겨 앞서간 경우 포함) 남의
    # 최신 토큰도 같은 세션이라 함께 끊긴다(앱 리뷰 66차, 화폐 재리뷰). 주인이면 이 기기만 다시 로그인한다
    if old and old["mine"]:
        revoke(c, old["account_id"], old["sid"])
        return None
    if old:
        revoke_all(c, old["account_id"])
        _notify(c, old["account_id"], "security", lang)
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
    """모든 세션 폐기 + 인증 버전 증가(발급된 액세스·미소비 인증 토큰도 무효).
    계정 행 → 세션 행 순으로 잠근다 — 비밀번호 변경·갱신 다시 받기와 같은 순서라야 서로 교착하지 않는다(앱 리뷰 45·47차)."""
    c.execute("UPDATE accounts SET auth_version = auth_version + 1 WHERE id = %s", (account_id,))
    c.execute("UPDATE sessions SET revoked_at = now() WHERE account_id = %s AND revoked_at IS NULL", (account_id,))


def _notify(c, account_id: int, kind: str, lang: str = "en") -> None:
    r = c.execute("SELECT email FROM accounts WHERE id = %s", (account_id,)).fetchone()
    if r and r["email"]:
        mail.send(r["email"], kind, protect_path(c, account_id), lang)


def sweep(c) -> None:
    """30일 지난 회전 이력 정리(주기 작업)."""
    c.execute(f"DELETE FROM spent_refresh WHERE spent_at < now() - interval '{IDLE}'")
