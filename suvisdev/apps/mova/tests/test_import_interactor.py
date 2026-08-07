from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.outbound.http.tmdb_mapper import (  # noqa: E402
    map_tmdb_row,
    tmdb_rating,
    tmdb_slug,
)
from mova.app.dtos.studio_import_dto import TmdbImportCommand  # noqa: E402
from mova.app.use_cases.import_interactor import ImportInteractor  # noqa: E402


class TmdbMapperTests(unittest.TestCase):
    def test_slug_and_rating(self) -> None:
        self.assertEqual(tmdb_slug(550), "tmdb-550")
        self.assertEqual(tmdb_rating(8.4), 4.2)
        self.assertEqual(tmdb_rating(None), 0.0)

    def test_map_popular_row(self) -> None:
        row = {
            "id": 27205,
            "title": "인셉션",
            "release_date": "2010-07-16",
            "vote_average": 8.8,
            "genre_ids": [28, 878],
            "poster_path": "/abc.jpg",
        }
        mapped = map_tmdb_row(
            row, genre_map={28: "액션", 878: "SF"}, poster_url="https://img/x.jpg"
        )
        assert mapped is not None
        self.assertEqual(mapped.slug, "tmdb-27205")
        self.assertEqual(mapped.release_year, 2010)
        self.assertEqual(mapped.genres, ["액션", "SF"])


class ImportInteractorTests(unittest.IsolatedAsyncioTestCase):
    async def test_seed_skips_when_catalog_full(self) -> None:
        movies = AsyncMock()
        movies.count_movies.return_value = 10
        interactor = ImportInteractor(movies, AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock())

        result = await interactor.seed_catalog_if_sparse()

        self.assertEqual(result.imported, 0)
        movies.count_movies.assert_awaited_once()

    async def test_import_by_tmdb_id(self) -> None:
        from mova.app.dtos.studio_import_dto import TmdbMovieSnapshotDto

        snap = TmdbMovieSnapshotDto(
            tmdb_id=1,
            slug="tmdb-1",
            title="Test",
            release_year=2020,
            rating=4.0,
            poster_url="",
            genres=["SF"],
        )
        catalog = AsyncMock()
        catalog.fetch_by_id.return_value = snap
        movies = AsyncMock()
        movies.upsert_movie.return_value = 42
        rankings = AsyncMock()
        interactor = ImportInteractor(movies, catalog, rankings, AsyncMock(), AsyncMock())

        result = await interactor.import_tmdb(TmdbImportCommand(tmdb_id=1))

        self.assertEqual(result.imported, 1)
        self.assertEqual(result.movie_ids, [42])
        movies.upsert_movie.assert_awaited_once()

    async def test_hub_ingest_uses_movie_id_not_slug_as_source_ref(self) -> None:
        """hub_knowledge.source_ref는 movie.id여야 한다.

        채팅이 이 값을 movie_id로 int() 파싱해 후보 집합을 만든다
        (chat_reply.enrich_from_db) — slug("tmdb-1")를 넣으면 파싱이 조용히
        실패해 추천이 전부 드롭된다.
        """
        from mova.app.dtos.studio_import_dto import TmdbMovieSnapshotDto

        snap = TmdbMovieSnapshotDto(
            tmdb_id=1,
            slug="tmdb-1",
            title="Test",
            release_year=2020,
            rating=4.0,
            poster_url="",
            genres=["SF"],
        )
        catalog = AsyncMock()
        catalog.fetch_by_id.return_value = snap
        movies = AsyncMock()
        movies.upsert_movie.return_value = 42
        hub_rag = AsyncMock()
        interactor = ImportInteractor(movies, catalog, AsyncMock(), AsyncMock(), hub_rag)

        await interactor.import_tmdb(TmdbImportCommand(tmdb_id=1))

        command = hub_rag.ingest_movie.await_args.args[0]
        self.assertEqual(command.source_ref, "42")
        self.assertNotEqual(command.source_ref, snap.slug)
        self.assertTrue(command.source_ref.isdigit())


if __name__ == "__main__":
    unittest.main()
