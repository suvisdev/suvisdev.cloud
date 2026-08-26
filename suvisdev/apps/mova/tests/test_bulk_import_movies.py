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
from mova.app.dtos.studio_import_dto import TmdbMovieSnapshotDto  # noqa: E402


class TmdbAdapterDiscoverTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_discover_calls_discover_endpoint_with_params(self) -> None:
        adapter = TmdbAdapter("fake-key")
        adapter._get = AsyncMock(return_value={"results": [{"id": 1, "title": "테스트"}]})

        rows = await adapter.fetch_discover(
            page=2, with_origin_country="KR", sort_by="popularity.desc"
        )

        adapter._get.assert_awaited_once_with(
            "/discover/movie",
            params={
                "page": 2,
                "sort_by": "popularity.desc",
                "include_adult": "false",
                "with_origin_country": "KR",
            },
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
            ["--source", "tmdb_discover", "--country", "KR", "--pages", "5", "--start-page", "31"]
        )
        self.assertEqual(args.source, "tmdb_discover")
        self.assertEqual(args.country, "KR")
        self.assertEqual(args.start_page, 31)

    def test_invalid_source_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            self._parse_args(["--source", "naver", "--pages", "1"])

    def test_missing_required_args_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            self._parse_args([])


class IngestTmdbMovieRollbackTests(unittest.IsolatedAsyncioTestCase):
    """실측 버그 회귀 테스트 — 영화 1건 실패가 세션을 오염시켜 이후 전 영화가
    PendingRollbackError로 도미노 실패하던 것(2026-08-04, EC2 실 배치에서
    418건 연쇄 실패로 발견). 각 except 블록이 session.rollback()을 호출해
    실패를 그 영화 하나로 격리하는지 검증한다."""

    @classmethod
    def setUpClass(cls) -> None:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from scripts.bulk_import_movies import _ingest_tmdb_movie

        cls._ingest_tmdb_movie = staticmethod(_ingest_tmdb_movie)

    def _snap(self) -> TmdbMovieSnapshotDto:
        return TmdbMovieSnapshotDto(
            tmdb_id=1,
            slug="tmdb-1",
            title="테스트 영화",
            release_year=2026,
            rating=8.0,
            poster_url="",
            genres=["드라마"],
        )

    async def test_upsert_failure_rolls_back_and_returns_failed(self) -> None:
        movies_repo = AsyncMock()
        movies_repo.upsert_movie.side_effect = Exception(
            "value too long for type character varying(50)"
        )
        hub_rag = AsyncMock()
        credits_interactor = AsyncMock()
        session = AsyncMock()

        outcome, skipped_cast, skipped_directors = await self._ingest_tmdb_movie(
            self._snap(), movies_repo, hub_rag, credits_interactor, session
        )

        self.assertEqual(outcome, "failed")
        self.assertEqual((skipped_cast, skipped_directors), (0, 0))
        session.rollback.assert_awaited_once()
        credits_interactor._backfill_one.assert_not_awaited()

    async def test_credits_failure_rolls_back_but_movie_still_succeeds(self) -> None:
        movies_repo = AsyncMock()
        movies_repo.upsert_movie.return_value = 42
        hub_rag = AsyncMock()
        credits_interactor = AsyncMock()
        credits_interactor._backfill_one.side_effect = Exception("credits boom")
        session = AsyncMock()

        outcome, skipped_cast, skipped_directors = await self._ingest_tmdb_movie(
            self._snap(), movies_repo, hub_rag, credits_interactor, session
        )

        self.assertEqual(outcome, "succeeded")
        self.assertEqual((skipped_cast, skipped_directors), (0, 0))
        session.rollback.assert_awaited_once()
        hub_rag.ingest_movie.assert_awaited_once()

    async def test_next_movie_after_a_failure_uses_a_clean_session(self) -> None:
        """도미노 실패 회귀의 핵심 — 첫 영화가 실패해도 두 번째 영화는 정상 처리돼야 한다."""
        movies_repo = AsyncMock()
        movies_repo.upsert_movie.side_effect = [Exception("boom"), 42]
        hub_rag = AsyncMock()
        credits_interactor = AsyncMock()
        session = AsyncMock()

        first, _, _ = await self._ingest_tmdb_movie(
            self._snap(), movies_repo, hub_rag, credits_interactor, session
        )
        second, _, _ = await self._ingest_tmdb_movie(
            self._snap(), movies_repo, hub_rag, credits_interactor, session
        )

        self.assertEqual(first, "failed")
        self.assertEqual(second, "succeeded")
        self.assertEqual(session.rollback.await_count, 1)

    async def test_partial_credits_skip_is_reported_not_hidden(self) -> None:
        """credits는 부분 성공(일부 cast/director 스킵)해도 영화 자체는 succeeded —
        그 스킵 건수가 반환값으로 노출되는지 확인(2026-08-05, failed=0에 안 잡히던
        유실을 배치 리포트에서 볼 수 있게 하는 게 목적)."""
        from mova.app.dtos.studio_import_dto import BackfillOneResultDto

        movies_repo = AsyncMock()
        movies_repo.upsert_movie.return_value = 42
        hub_rag = AsyncMock()
        credits_interactor = AsyncMock()
        credits_interactor._backfill_one.return_value = BackfillOneResultDto(
            skipped_cast=3, skipped_directors=1
        )
        session = AsyncMock()

        outcome, skipped_cast, skipped_directors = await self._ingest_tmdb_movie(
            self._snap(), movies_repo, hub_rag, credits_interactor, session
        )

        self.assertEqual(outcome, "succeeded")
        self.assertEqual((skipped_cast, skipped_directors), (3, 1))


if __name__ == "__main__":
    unittest.main()
