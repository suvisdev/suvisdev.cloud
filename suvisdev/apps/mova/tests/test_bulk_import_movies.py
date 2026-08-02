"""TMDB discover 어댑터 + scripts/bulk_import_movies.py CLI 인자 파싱 유닛 테스트."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.outbound.http.tmdb_adapter import TmdbAdapter  # noqa: E402


class TmdbAdapterDiscoverTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_discover_calls_discover_endpoint_with_params(self) -> None:
        adapter = TmdbAdapter("fake-key")
        adapter._get = AsyncMock(return_value={"results": [{"id": 1, "title": "테스트"}]})

        rows = await adapter.fetch_discover(
            page=2, with_origin_country="KR", sort_by="popularity.desc"
        )

        adapter._get.assert_awaited_once_with(
            "/discover/movie",
            params={"page": 2, "sort_by": "popularity.desc", "with_origin_country": "KR"},
        )
        self.assertEqual(rows, [{"id": 1, "title": "테스트"}])

    async def test_fetch_discover_no_results_returns_empty_list(self) -> None:
        adapter = TmdbAdapter("fake-key")
        adapter._get = AsyncMock(return_value={})

        rows = await adapter.fetch_discover(page=1)

        self.assertEqual(rows, [])


class ParseArgsTests(unittest.TestCase):
    """scripts/bulk_import_movies.py --source/--country/--pages/--start-page 인자 파싱."""

    @classmethod
    def setUpClass(cls) -> None:
        suvisdev_root = ROOT
        if str(suvisdev_root) not in sys.path:
            sys.path.insert(0, str(suvisdev_root))
        from scripts.bulk_import_movies import _parse_args

        cls._parse_args = staticmethod(_parse_args)

    def test_required_source_and_pages(self) -> None:
        args = self._parse_args(["--source", "tmdb_discover", "--pages", "10"])
        self.assertEqual(args.source, "tmdb_discover")
        self.assertEqual(args.pages, 10)
        self.assertEqual(args.country, "ALL")
        self.assertEqual(args.start_page, 1)

    def test_start_page_for_resume(self) -> None:
        args = self._parse_args(
            ["--source", "kofic", "--country", "KR", "--pages", "5", "--start-page", "31"]
        )
        self.assertEqual(args.source, "kofic")
        self.assertEqual(args.country, "KR")
        self.assertEqual(args.start_page, 31)

    def test_invalid_source_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            self._parse_args(["--source", "naver", "--pages", "1"])

    def test_missing_required_args_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            self._parse_args([])


if __name__ == "__main__":
    unittest.main()
