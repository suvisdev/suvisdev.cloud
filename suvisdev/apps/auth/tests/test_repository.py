from __future__ import annotations

import hashlib

from auth.repository import _hash_password, _verify_password


def test_verify_password_matches_legacy_sha256_digest():
    digest = hashlib.sha256(b"admin1234").hexdigest()
    assert _verify_password("admin1234", digest) is True


def test_verify_password_rejects_wrong_password_for_legacy_digest():
    digest = hashlib.sha256(b"admin1234").hexdigest()
    assert _verify_password("wrong", digest) is False


def test_verify_password_rejects_raw_equality():
    """평문 동등 비교는 pass-the-hash 경로라 제거됨(2026-09-11) — 저장값을
    그대로 제출해도 통과하면 안 된다."""
    assert _verify_password("plaintext", "plaintext") is False


def test_verify_password_rejects_hash_submitted_as_password():
    """sha256 해시 유출 시 그 해시를 비밀번호로 제출하는 pass-the-hash 차단."""
    digest = hashlib.sha256(b"admin1234").hexdigest()
    assert _verify_password(digest, digest) is False


def test_hash_password_produces_bcrypt_hash():
    hashed = _hash_password("s3cure-pass")
    assert hashed.startswith(("$2a$", "$2b$", "$2y$"))


def test_verify_password_matches_bcrypt_hash():
    hashed = _hash_password("s3cure-pass")
    assert _verify_password("s3cure-pass", hashed) is True


def test_verify_password_rejects_wrong_password_for_bcrypt_hash():
    hashed = _hash_password("s3cure-pass")
    assert _verify_password("wrong-pass", hashed) is False
