from __future__ import annotations

from auth.repository import _verify_legacy_sha256_password


def test_verify_legacy_sha256_password_matches_digest():
    import hashlib

    digest = hashlib.sha256(b"admin1234").hexdigest()
    assert _verify_legacy_sha256_password("admin1234", digest) is True


def test_verify_legacy_sha256_password_rejects_wrong_password():
    import hashlib

    digest = hashlib.sha256(b"admin1234").hexdigest()
    assert _verify_legacy_sha256_password("wrong", digest) is False


def test_verify_legacy_sha256_password_allows_raw_fallback():
    """viewer LoginPgRepository._verify_password와 동일하게 평문 저장 폴백도 허용."""
    assert _verify_legacy_sha256_password("plaintext", "plaintext") is True
