"""비밀번호 정책·해시(SECURITY.md 1절 '비밀번호', 검증 2)."""

import hashlib
import threading
from pathlib import Path

import httpx
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# SECURITY.md: 64MB·반복 3·병렬 1에서 시작해 약 0.3초로 조정. 노트북 실측(11-21): 반복 3 = 0.12초, 8 = 0.28초 → 8.
PH = PasswordHasher(time_cost=8, memory_cost=65536, parallelism=1)
MIN, MAX, MAX_BYTES = 8, 128, 512  # 8자 이상 + 문자·숫자 섞기(11-27 사용자, ADR-0027)
HIBP = "https://api.pwnedpasswords.com/range/"
# 해시는 한 번에 64MB를 쓴다 → 동시에 2개까지만(파드 메모리 한도). 자리가 안 나면 기다리다 Busy.
_slots = threading.BoundedSemaphore(2)
# 조회 장애 때 쓰는 로컬 유출 목록(SHA-1 대문자 한 줄씩). 없으면 장애 동안 가입·변경·재설정을 보류한다.
LOCAL = Path(__file__).parent / "pwned_local.txt"
_dummy: str | None = None


class Busy(Exception):
    """해시 자리가 안 남(서비스 거부 방지) → 503."""


def too_long(pw: str) -> bool:
    return len(pw) > MAX or len(pw.encode()) > MAX_BYTES


def check(pw: str, email: str | None, nickname: str | None, client: httpx.Client | None = None) -> str | None:
    """거부 이유(short·long·weak·personal·breached·unavailable) 또는 None. 문자(한글 포함)와 숫자가 둘 다 있어야 한다."""
    if len(pw) < MIN:
        return "short"
    if too_long(pw):
        return "long"
    if not (any(ch.isalpha() for ch in pw) and any(ch.isdigit() for ch in pw)):
        return "weak"
    same = {(email or "").lower(), (email or "").split("@")[0].lower(), (nickname or "").lower()} - {""}
    if pw.strip().lower() in same:
        return "personal"
    sha = hashlib.sha1(pw.encode()).hexdigest().upper()
    try:
        # k-익명성: 앞 5자리만 보낸다. Add-Padding은 응답 크기로 무엇을 물었는지 알 수 없게 한다.
        r = (client or httpx).get(HIBP + sha[:5], headers={"Add-Padding": "true"}, timeout=3)
        r.raise_for_status()
        hit = any(
            (p := line.split(":"))[0] == sha[5:] and p[1].strip() != "0" for line in r.text.splitlines() if ":" in line
        )
    except httpx.HTTPError:
        if not LOCAL.exists():
            return "unavailable"
        hit = sha in LOCAL.read_text().split()
    return "breached" if hit else None


def _hashing():
    if not _slots.acquire(timeout=5):
        raise Busy
    return _slots


def hash(pw: str) -> str:  # noqa: A001 — 모듈 이름으로 passwords.hash(…)라 읽힌다
    slot = _hashing()
    try:
        return PH.hash(pw)
    finally:
        slot.release()


def verify(h: str | None, pw: str) -> tuple[bool, str | None]:
    """(맞는지, 다시 해시한 값 또는 None). 계정이 없거나 비밀번호가 없는 계정도 같은 시간이 걸리게 더미 해시로 검사한다."""
    global _dummy
    if too_long(pw):
        return False, None
    if h is None:
        if _dummy is None or PH.check_needs_rehash(_dummy):  # 해시 설정이 바뀌면 더미도 같은 비용으로
            _dummy = PH.hash("kumoniji-dummy-password-for-timing")
    slot = _hashing()
    try:
        try:
            PH.verify(h or _dummy, pw)
        except (VerificationError, InvalidHashError):
            return False, None
        if h is None:
            return False, None
        return True, PH.hash(pw) if PH.check_needs_rehash(h) else None
    finally:
        slot.release()
