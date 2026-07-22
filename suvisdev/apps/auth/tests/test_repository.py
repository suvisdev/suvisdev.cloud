from __future__ import annotations

import hashlib

from auth.repository import _hash_password, _verify_password


def test_verify_password_matches_legacy_sha256_digest():
    digest = hashlib.sha256(b"admin1234").hexdigest()
    assert _verify_password("admin1234", digest) is True


def test_verify_password_rejects_wrong_password_for_legacy_digest():
    digest = hashlib.sha256(b"admin1234").hexdigest()
    assert _verify_password("wrong", digest) is False


def test_verify_password_allows_legacy_raw_fallback():
    """viewer LoginPgRepository._verify_password와 동일하게 평문 저장 폴백도 허용."""
    assert _verify_password("plaintext", "plaintext") is True


def test_hash_password_produces_bcrypt_hash():
    hashed = _hash_password("s3cure-pass")
    assert hashed.startswith(("$2a$", "$2b$", "$2y$"))


def test_verify_password_matches_bcrypt_hash():
    hashed = _hash_password("s3cure-pass")
    assert _verify_password("s3cure-pass", hashed) is True


def test_verify_password_rejects_wrong_password_for_bcrypt_hash():
    hashed = _hash_password("s3cure-pass")
    assert _verify_password("wrong-pass", hashed) is False
