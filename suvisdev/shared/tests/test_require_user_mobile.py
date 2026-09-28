"""길들 앱(aud=suvis-susu) 토큰도 로그인 가드를 통과한다(2026-09-28 — 전엔 앱 산책 저장이 401)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from shared.security.require_user import require_user
from shared.tests.test_token_verifier import _sign


@pytest.mark.parametrize("aud", ["suvis-mova", "suvis-susu"])
def test_web_and_mobile_tokens_pass(rsa_keypair, aud):
    private_pem, _ = rsa_keypair
    principal = require_user(f"Bearer {_sign(private_pem, aud=aud, roles=['user'])}")
    assert principal.user_id > 0 and principal.role == "user"


def test_other_audience_still_rejected(rsa_keypair):
    private_pem, _ = rsa_keypair
    with pytest.raises(HTTPException) as e:
        require_user(f"Bearer {_sign(private_pem, aud='suvis-other', roles=['user'])}")
    assert e.value.status_code == 401
