"""scripts/backfill_original_language_cli.py — 인자 파싱 + 영화 1편 처리(_backfill_one) 유닛 테스트."""

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

from scripts.backfill_original_language_cli import _backfill_one, _parse_args  # noqa: E402


class ParseArgsTests(unittest.TestCase):
    def test_defaults_are_full_run(self) -> None:
        args = _parse_args([])
        self.assertIsNone(args.limit)
        self.assertFalse(args.dry_run)

    def test_limit_and_dry_run_combined(self) -> None:
        args = _parse_args(["--limit", "5", "--dry-run"])
        self.assertEqual(args.limit, 5)
        self.assertTrue(args.dry_run)


class BackfillOneTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_tmdb_slug_is_skipped_without_fetch(self) -> None:
        movies_repo = AsyncMock()
        catalog = AsyncMock()

        outcome = await _backfill_one(
            movies_repo, catalog, 1, "hand-curated-movie", dry_run=False
        )

        self.assertEqual(outcome, "skipped")
        catalog.fetch_by_id.assert_not_awaited()

    async def test_dry_run_does_not_write(self) -> None:
        movies_repo = AsyncMock()
        catalog = AsyncMock()
        catalog.fetch_by_id.return_value = SimpleNamespace(original_language="th")

        outcome = await _backfill_one(movies_repo, catalog, 1, "tmdb-550", dry_run=True)

        self.assertEqual(outcome, "succeeded")
        movies_repo.update_original_language.assert_not_awaited()

    async def test_real_run_writes_original_language(self) -> None:
        movies_repo = AsyncMock()
        catalog = AsyncMock()
        catalog.fetch_by_id.return_value = SimpleNamespace(original_language="th")

        outcome = await _backfill_one(movies_repo, catalog, 1, "tmdb-550", dry_run=False)

        self.assertEqual(outcome, "succeeded")
        movies_repo.update_original_language.assert_awaited_once_with(1, "th")

    async def test_empty_original_language_is_skipped(self) -> None:
        movies_repo = AsyncMock()
        catalog = AsyncMock()
        catalog.fetch_by_id.return_value = SimpleNamespace(original_language="")

        outcome = await _backfill_one(movies_repo, catalog, 1, "tmdb-550", dry_run=False)

        self.assertEqual(outcome, "skipped")
        movies_repo.update_original_language.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
