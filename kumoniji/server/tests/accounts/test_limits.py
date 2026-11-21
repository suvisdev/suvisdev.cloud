"""검증 4: 열거·대입 방지(제한 부분). 응답 균일화는 test_web.py."""

import httpx

from kumoniji.accounts import db, limits


def test_4_sixth_failure_waits_one_second_and_caps_at_15_minutes(database):
    with db.tx() as c:
        for _ in range(5):
            assert limits.wait(c, "acct:a") == 0
            limits.fail(c, "acct:a")
        assert 0.5 < limits.wait(c, "acct:a") <= 1  # 5번 실패 → 6번째 전에 1초
        limits.fail(c, "acct:a")
        assert 1.5 < limits.wait(c, "acct:a") <= 2
        for _ in range(30):
            limits.fail(c, "acct:a")
        assert 890 < limits.wait(c, "acct:a") <= 900  # 상한 15분, 영구 잠금 없음
        limits.clear(c, "acct:a")
        assert limits.wait(c, "acct:a") == 0


def test_4_budget_per_minute(database):
    with db.tx() as c:
        assert all(limits.budget(c, "signup:ip:1.2.3.4", 3) for _ in range(3))
        assert not limits.budget(c, "signup:ip:1.2.3.4", 3)
        assert limits.budget(c, "signup:ip:5.6.7.8", 3)  # 다른 IP는 따로
        c.execute("UPDATE attempts SET seen = now() - interval '2 minutes' WHERE key = 'rate:signup:ip:1.2.3.4'")
        assert limits.budget(c, "signup:ip:1.2.3.4", 3)  # 1분이 지나면 다시


def test_4_captcha_after_ten_ip_failures_and_fails_closed(database, monkeypatch):
    with db.tx() as c:
        for _ in range(9):
            limits.fail(c, "ip:9.9.9.9")
        assert not limits.needs_captcha(c, "9.9.9.9")
        limits.fail(c, "ip:9.9.9.9")
        assert limits.needs_captcha(c, "9.9.9.9")
    ok = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"success": True})))
    down = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(502, text="bad gateway")))
    monkeypatch.delenv("KUMONIJI_TURNSTILE_SECRET", raising=False)
    assert not limits.captcha_ok("tok", "9.9.9.9", ok)  # 키가 없으면 닫힘
    monkeypatch.setenv("KUMONIJI_TURNSTILE_SECRET", "s")
    assert limits.captcha_ok("tok", "9.9.9.9", ok)
    assert not limits.captcha_ok("tok", "9.9.9.9", down)
    assert not limits.captcha_ok(None, "9.9.9.9", ok)
