"""검증 2: 비밀번호."""

import hashlib

import httpx
import pytest
from argon2 import PasswordHasher

from kumoniji.accounts import passwords

GOOD = "correct horse battery"  # 21자, 공백 포함 문장


def hibp(hit: str | None = None, fail: bool = False):
    def handler(request: httpx.Request):
        if fail:
            raise httpx.ConnectError("down")
        assert len(request.url.path.rsplit("/", 1)[1]) == 5  # 앞 5자리만 보낸다
        body = "0000000000000000000000000000000000A:0\n"  # 패딩 줄
        if hit:
            body += hashlib.sha1(hit.encode()).hexdigest().upper()[5:] + ":42\n"
        return httpx.Response(200, text=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_2_length_bounds():
    assert passwords.check("a" * 14, "x@y.z", "nick", hibp()) == "short"
    assert passwords.check("a" * 129, "x@y.z", "nick", hibp()) == "long"
    assert passwords.check(GOOD, "x@y.z", "nick", hibp()) is None


def test_2_rejects_email_and_nickname():
    assert passwords.check("longnickname1234", "x@y.z", "LongNickname1234", hibp()) == "personal"
    assert passwords.check("someone.long.email", "someone.long.email@y.z", "n", hibp()) == "personal"


def test_2_rejects_breached_and_holds_when_lookup_is_down(monkeypatch, tmp_path):
    assert passwords.check(GOOD, "x@y.z", "n", hibp(hit=GOOD)) == "breached"
    monkeypatch.setattr(passwords, "LOCAL", tmp_path / "none.txt")
    assert passwords.check(GOOD, "x@y.z", "n", hibp(fail=True)) == "unavailable"  # 보류
    local = tmp_path / "local.txt"
    local.write_text(hashlib.sha1(GOOD.encode()).hexdigest().upper() + "\n")
    monkeypatch.setattr(passwords, "LOCAL", local)
    assert passwords.check(GOOD, "x@y.z", "n", hibp(fail=True)) == "breached"
    assert passwords.check("another long phrase", "x@y.z", "n", hibp(fail=True)) is None


def test_2_argon2id_params_and_no_plaintext():
    h = passwords.hash(GOOD)
    assert h.startswith("$argon2id$v=19$m=65536,t=8,p=1$")
    assert GOOD not in h
    assert passwords.verify(h, GOOD) == (True, None)
    assert passwords.verify(h, GOOD + "x") == (False, None)


def test_2_rehash_weak_hash_on_login():
    weak = PasswordHasher(time_cost=3, memory_cost=8192, parallelism=1).hash(GOOD)
    ok, new = passwords.verify(weak, GOOD)
    assert ok and new.startswith("$argon2id$v=19$m=65536,t=8,p=1$")


def test_2_missing_account_takes_a_real_verify():
    assert passwords.verify(None, GOOD) == (False, None)
    assert passwords._dummy is not None


def test_4_oversized_input_is_rejected_before_hashing(monkeypatch):
    class Boom:
        def verify(self, *a):
            pytest.fail("해시 전에 거부해야 함")

    monkeypatch.setattr(passwords, "PH", Boom())
    assert passwords.verify("$argon2id$whatever", "가" * 200) == (False, None)
