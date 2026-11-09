"""고객 키 한 쌍 생성과 비밀 키 대조.

공개 키(pk_)는 SDK에 박혀 노출돼도 되고, 비밀 키(sk_)는 고객 서버만 안다.
비밀 키는 발급 응답에서 한 번만 보여 주고 DB에는 해시만 둔다 — DB가 새도 키는 안 샌다.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets


def new_site_key() -> str:
    return "pk_" + secrets.token_hex(16)


def new_secret_key() -> str:
    return "sk_" + secrets.token_hex(24)


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def secret_matches(secret: str, secret_hash: str) -> bool:
    return hmac.compare_digest(hash_secret(secret), secret_hash)
