"""계정 DB(Postgres, kumoniji-db 컨테이너). 연결 풀과 번호 붙은 .sql 마이그레이션."""

from contextlib import contextmanager
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

MIGRATIONS = Path(__file__).parent / "migrations"
_pool: ConnectionPool | None = None


def init(url: str) -> None:
    global _pool
    if _pool is not None:
        _pool.close()
    _pool = ConnectionPool(url, min_size=1, max_size=8, kwargs={"row_factory": dict_row}, open=True)
    with tx() as c:
        migrate(c)


def close() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def tx():
    """블록이 정상으로 끝나면 커밋, 예외면 롤백(psycopg_pool의 connection() 동작)."""
    if _pool is None:
        raise RuntimeError("계정 DB가 설정되지 않음(KUMONIJI_DATABASE_URL)")
    with _pool.connection() as c:
        yield c


def migrate(c) -> None:
    """적용 안 된 .sql만 순서대로. 파드가 둘 이상 동시에 떠도 잠금으로 한 번만."""
    c.execute("SELECT pg_advisory_xact_lock(20261121)")
    c.execute("CREATE TABLE IF NOT EXISTS schema_version (n integer PRIMARY KEY)")
    done = {r["n"] for r in c.execute("SELECT n FROM schema_version")}
    for f in sorted(MIGRATIONS.glob("*.sql")):
        n = int(f.name.split("_")[0])
        if n not in done:
            c.execute(f.read_text())
            c.execute("INSERT INTO schema_version VALUES (%s)", (n,))
