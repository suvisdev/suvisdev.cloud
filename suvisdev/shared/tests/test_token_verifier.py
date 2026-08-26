from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from shared.security.token_verifier import verify_token


def _sign(private_pem: str, *, aud: str, roles: list[str], expires_min: int = 10) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": "42",
            "roles": roles,
            "aud": aud,
            "iat": now,
            "exp": now + timedelta(minutes=expires_min),
            "jti": "test-jti",
        },
        private_pem,
        algorithm="RS256",
    )


def test_verify_token_accepts_token_signed_by_matching_private_key(rsa_keypair):
    private_pem, _ = rsa_keypair
    token = _sign(private_pem, aud="suvis-mova", roles=["user"])
    payload = verify_token(token, "suvis-mova")
    assert payload.sub == "42"
    assert payload.roles == ["user"]


def test_verify_token_rejects_wrong_audience(rsa_keypair):
    private_pem, _ = rsa_keypair
    token = _sign(private_pem, aud="suvis-mova", roles=["user"])
    with pytest.raises(jwt.InvalidAudienceError):
        verify_token(token, "suvis-gildle")
