"""검증 3: 인증 토큰."""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from kumoniji.accounts import db, tokens

from .helpers import make_account

DAY = timedelta(days=1)


def test_3_only_one_of_concurrent_consumes_wins(database):
    a = make_account()
    with db.tx() as c:
        raw = tokens.issue(c, a, "verify", DAY)

    def go(_):
        with db.tx() as c:
            return tokens.consume(c, raw, "verify")

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(go, range(20)))
    assert sum(r is not None for r in results) == 1


def test_3_wrong_purpose_expired_old_version_and_reissued_are_rejected(database):
    a = make_account()
    with db.tx() as c:
        raw = tokens.issue(c, a, "verify", DAY)
        assert tokens.consume(c, raw, "reset") is None  # 다른 목적
        old = tokens.issue(c, a, "reset", DAY)
        new = tokens.issue(c, a, "reset", DAY)
        assert tokens.consume(c, old, "reset") is None  # 새 요청이 이전 요청을 무효화
        expired = tokens.issue(c, a, "email", -DAY, target="b@x.com")
        assert tokens.consume(c, expired, "email") is None
        c.execute("UPDATE accounts SET auth_version = auth_version + 1 WHERE id = %s", (a,))
        assert tokens.consume(c, raw, "verify") is None  # 비밀번호·주소가 바뀌면 옛 토큰 무효
        assert tokens.consume(c, new, "reset") is None


def test_3_token_is_bound_to_its_account_and_target_and_stored_hashed(database):
    a, b = make_account("a@x.com"), make_account("b@x.com")
    with db.tx() as c:
        ra = tokens.issue(c, a, "email", DAY, target="new@x.com")
        tokens.issue(c, b, "email", DAY, target="other@x.com")
        stored = [bytes(r["hash"]) for r in c.execute("SELECT hash FROM auth_tokens")]
        assert ra.encode() not in stored and tokens.digest(ra) in stored
        assert tokens.peek(c, ra, "email")
        assert tokens.consume(c, ra, "email") == {"account_id": a, "target": "new@x.com"}
        assert not tokens.peek(c, ra, "email")


def test_3_peek_does_not_consume(database):
    a = make_account()
    with db.tx() as c:
        raw = tokens.issue(c, a, "verify", DAY)
        assert tokens.peek(c, raw, "verify") and tokens.peek(c, raw, "verify")
        assert tokens.consume(c, raw, "verify") is not None


def test_3_concurrent_issues_leave_only_the_newest_valid(database):
    a = make_account()
    first_inside, out = threading.Event(), {}

    def first():
        with db.tx() as c:
            out["a"] = tokens.issue(c, a, "reset", timedelta(minutes=30))
            first_inside.set()
            threading.Event().wait(0.5)  # 커밋 전에 두 번째 요청이 들어온다

    def second():
        first_inside.wait()
        with db.tx() as c:
            out["b"] = tokens.issue(c, a, "reset", timedelta(minutes=30))

    ts = [threading.Thread(target=first), threading.Thread(target=second)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    with db.tx() as c:
        valid = [k for k in ("a", "b") if tokens.peek(c, out[k], "reset")]
    assert valid == ["b"]
