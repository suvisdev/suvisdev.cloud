from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import jwt as pyjwt
import pytest

from auth.security import JwtAdapter, _load_public_key


def _b64url(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def test_verify_succeeds_with_public_key_only(rsa_keypair):
    adapter = JwtAdapter()
    token = adapter.issue_access_token("42", ["user"], "suvis-mova")
    payload = adapter.verify(token, "suvis-mova")
    assert payload.sub == "42"
    assert payload.roles == ["user"]
    assert payload.aud == "suvis-mova"


def test_verify_rejects_wrong_audience(rsa_keypair):
    adapter = JwtAdapter()
    token = adapter.issue_access_token("42", ["user"], "suvis-mova")
    with pytest.raises(pyjwt.InvalidAudienceError):
        adapter.verify(token, "suvis-gildle")


def test_verify_rejects_expired_token(rsa_keypair):
    adapter = JwtAdapter()
    token = adapter.issue_access_token("42", ["user"], "suvis-mova", expires_min=-1)
    with pytest.raises(pyjwt.ExpiredSignatureError):
        adapter.verify(token, "suvis-mova")


def test_verify_rejects_tampered_signature(rsa_keypair):
    adapter = JwtAdapter()
    token = adapter.issue_access_token("42", ["user"], "suvis-mova")
    tampered = token[:-4] + ("A" if token[-4] != "A" else "B") + token[-3:]
    with pytest.raises(pyjwt.InvalidSignatureError):
        adapter.verify(tampered, "suvis-mova")


def test_verify_rejects_alg_none_forged_token(rsa_keypair):
    adapter = JwtAdapter()
    header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64url(
        json.dumps(
            {"sub": "42", "roles": ["admin"], "aud": "suvis-mova", "exp": int(time.time()) + 600, "iat": int(time.time()), "jti": "x"}
        ).encode()
    )
    forged = (header + b"." + payload + b".").decode()
    with pytest.raises(pyjwt.InvalidAlgorithmError):
        adapter.verify(forged, "suvis-mova")


def test_verify_rejects_hs256_key_confusion_attack(rsa_keypair):
    """RS256 공개키를 HMAC 비밀키로 재사용하는 알고리즘 혼동 공격 방어 확인."""
    adapter = JwtAdapter()
    pub_pem = _load_public_key().encode()
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(
        json.dumps(
            {"sub": "42", "roles": ["admin"], "aud": "suvis-mova", "exp": int(time.time()) + 600, "iat": int(time.time()), "jti": "x"}
        ).encode()
    )
    signing_input = header + b"." + payload
    sig = hmac.new(pub_pem, signing_input, hashlib.sha256).digest()
    forged = (signing_input + b"." + _b64url(sig)).decode()
    with pytest.raises(pyjwt.InvalidAlgorithmError):
        adapter.verify(forged, "suvis-mova")


def test_build_jwks_contains_kid_and_no_private_material(rsa_keypair):
    adapter = JwtAdapter()
    jwks = adapter.build_jwks()
    key = jwks["keys"][0]
    assert key["kid"] == "test-kid"
    assert key["alg"] == "RS256"
    assert "d" not in key  # RSA 개인지수 — 있으면 개인키 유출
