"""scripts/backfill_origin_country_cli.py — _backfill_one 유닛 테스트.

빈 배열도 기록해야(NULL로 남기지 않아야) 재실행 시 같은 영화를 다시 조회하지
않는다는 계약이 핵심이다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.backfill_origin_country_cli import _backfill_one, _parse_args  # noqa: E402


class ParseArgsTests(unittest.TestCase):
    def test_defaults_are_full_run(self) -> None:
        args = _parse_args([])
        self.assertIsNone(args.limit)
        self.assertFalse(args.dry_run)


class BackfillOneTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_tmdb_slug_is_skipped_without_fetch(self) -> None:
        movies_repo = AsyncMock()
        catalog = AsyncMock()

        outcome = await _backfill_one(movies_repo, catalog, 1, "hand-curated", dry_run=False)

        self.assertEqual(outcome, "skipped")
        catalog.fetch_by_id.assert_not_awaited()
        movies_repo.update_origin_country.assert_not_awaited()

    async def test_writes_country_list(self) -> None:
        movies_repo = AsyncMock()
        catalog = AsyncMock()
        catalog.fetch_by_id.return_value = SimpleNamespace(origin_country=["US", "GB"])

        outcome = await _backfill_one(movies_repo, catalog, 1, "tmdb-550", dry_run=False)

        self.assertEqual(outcome, "succeeded")
        movies_repo.update_origin_country.assert_awaited_once_with(1, ["US", "GB"])

    async def test_empty_country_is_still_written(self) -> None:
        """NULL로 남기면 '백필 안 됨'과 구분이 안 돼 매번 재조회된다."""
        movies_repo = AsyncMock()
        catalog = AsyncMock()
        catalog.fetch_by_id.return_value = SimpleNamespace(origin_country=[])

        outcome = await _backfill_one(movies_repo, catalog, 1, "tmdb-550", dry_run=False)

        self.assertEqual(outcome, "empty")
        movies_repo.update_origin_country.assert_awaited_once_with(1, [])

    async def test_dry_run_does_not_write(self) -> None:
        movies_repo = AsyncMock()
        catalog = AsyncMock()
        catalog.fetch_by_id.return_value = SimpleNamespace(origin_country=["KR"])

        outcome = await _backfill_one(movies_repo, catalog, 1, "tmdb-550", dry_run=True)

        self.assertEqual(outcome, "succeeded")
        movies_repo.update_origin_country.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
