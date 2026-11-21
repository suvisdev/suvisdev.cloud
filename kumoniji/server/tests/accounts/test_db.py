from kumoniji.accounts import db


def test_migrate_creates_tables_and_is_idempotent(database):
    with db.tx() as c:
        db.migrate(c)  # 두 번째 적용 — 아무것도 바뀌지 않아야 한다
        tables = {
            r["table_name"]
            for r in c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        }
        versions = [r["n"] for r in c.execute("SELECT n FROM schema_version")]
    assert {"accounts", "identities", "auth_tokens", "sessions", "recovery_codes", "attempts"} <= tables
    assert versions == [1, 2]
