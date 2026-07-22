from __future__ import annotations

import importlib

import pytest


def test_import_does_not_require_private_key(monkeypatch):
    monkeypatch.delenv("JWT_PRIVATE_KEY_B64", raising=False)
    monkeypatch.delenv("JWT_PUBLIC_KEY_B64", raising=False)
    module = importlib.import_module("auth.security")
    importlib.reload(module)  # 이미 import된 경우에도 이 조건에서 재로딩이 안전한지 확인


def test_issue_access_token_raises_without_private_key(monkeypatch):
    monkeypatch.delenv("JWT_PRIVATE_KEY_B64", raising=False)
    from auth.security import JwtAdapter

    with pytest.raises(RuntimeError):
        JwtAdapter().issue_access_token("1", ["user"], "suvis-mova")
