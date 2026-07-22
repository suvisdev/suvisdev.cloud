import base64
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_here = Path(__file__).parent  # apps/auth/tests/

_paths = [
    _here.parent.parent,            # apps/     → auth.* 임포트
    _here.parent.parent.parent,     # suvisdev/ → core.* 임포트
]
for _p in _paths:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


@pytest.fixture()
def rsa_keypair(monkeypatch) -> tuple[str, str]:
    """테스트용 RSA-2048 키페어를 생성해 JWT_PRIVATE_KEY_B64/JWT_PUBLIC_KEY_B64 env로 주입한다."""
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
