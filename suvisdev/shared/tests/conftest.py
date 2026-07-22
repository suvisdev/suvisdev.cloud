import base64
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_here = Path(__file__).parent  # shared/tests/

_paths = [
    _here.parent.parent,  # suvisdev/ → shared.*, auth.*(테스트에서 발급용으로만) 임포트
    _here.parent.parent / "apps",
]
for _p in _paths:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


@pytest.fixture()
def rsa_keypair(monkeypatch) -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    monkeypatch.setenv("JWT_PRIVATE_KEY_B64", base64.b64encode(private_pem).decode())
    monkeypatch.setenv("JWT_PUBLIC_KEY_B64", base64.b64encode(public_pem).decode())
    monkeypatch.setenv("JWT_KID", "test-kid")
    return private_pem.decode(), public_pem.decode()
