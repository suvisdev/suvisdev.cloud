"""TMDB credits 백필 — 매퍼(순수 함수)·인터랙터(오케스트레이션) 유닛 테스트.

repository upsert의 실제 멱등성/동명이인 분리는 Postgres 없이는 검증할 수
없어(로컬 Docker 데몬 미연결) 이 파일 범위 밖이다 — 실 DB 검증은 EC2에서
마이그레이션 적용 후 진행한다. 여기서는 map_credits()의 person id 기준
중복 제거(같은 응답 안 dedup)와, CreditsBackfillInteractor가 Port를 올바른
순서·인자로 호출하는지, 실패 시 나머지 영화 처리를 막지 않는지를 검증한다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.outbound.http.tmdb_mapper import map_credits  # noqa: E402
from mova.app.dtos.studio_import_dto import TmdbCreditsDto  # noqa: E402
from mova.app.use_cases.credits_backfill_interactor import (  # noqa: E402
    CreditsBackfillInteractor,
    _parse_tmdb_id,
)


class MapCreditsTests(unittest.TestCase):
    def test_no_credits_returns_empty(self) -> None:
        result = map_credits(None)
        self.assertEqual(result, TmdbCreditsDto())

    def test_cast_without_crew_has_no_directors(self) -> None:
        result = map_credits(
            {
                "cast": [
                    {"id": 1, "name": "배우A", "character": "역할1", "order": 0},
                ],
                "crew": [],
            }
        )
        self.assertEqual(len(result.cast), 1)
        self.assertEqual(result.cast[0].tmdb_person_id, 1)
        self.assertEqual(result.cast[0].character, "역할1")
        self.assertEqual(result.directors, [])

    def test_crew_job_filter_excludes_non_director(self) -> None:
        result = map_credits(
            {
                "cast": [],
                "crew": [
                    {"id": 10, "name": "프로듀서A", "job": "Producer"},
                    {"id": 11, "name": "촬영감독A", "job": "Director of Photography"},
                ],
            }
        )
        self.assertEqual(result.directors, [])

    def test_crew_multiple_directors_co_direction(self) -> None:
        result = map_credits(
            {
                "cast": [],
                "crew": [
                    {"id": 20, "name": "감독A", "job": "Director"},
                    {"id": 21, "name": "감독B", "job": "Director"},
                ],
            }
        )
        self.assertEqual(len(result.directors), 2)
        self.assertEqual({d.tmdb_person_id for d in result.directors}, {20, 21})

    def test_duplicate_cast_person_id_deduplicated(self) -> None:
        result = map_credits(
            {
                "cast": [
                    {"id": 1, "name": "배우A", "character": "역할1", "order": 0},
                    {"id": 1, "name": "배우A", "character": "역할1(중복)", "order": 5},
                ],
                "crew": [],
            }
        )
        self.assertEqual(len(result.cast), 1)

    def test_cast_limit_applied(self) -> None:
        cast = [{"id": i, "name": f"배우{i}", "character": "역", "order": i} for i in range(15)]
        result = map_credits({"cast": cast, "crew": []}, cast_limit=10)
        self.assertEqual(len(result.cast), 10)

    def test_profile_path_maps_to_absolute_url(self) -> None:
        result = map_credits(
            {
                "cast": [
                    {
                        "id": 1,
                        "name": "배우A",
                        "character": "역할1",
                        "order": 0,
                        "profile_path": "/abc.jpg",
                    }
                ],
                "crew": [],
            }
        )
        self.assertTrue(result.cast[0].profile_photo_url.endswith("/abc.jpg"))


class ParseTmdbIdTests(unittest.TestCase):
    def test_parses_tmdb_prefixed_slug(self) -> None:
        self.assertEqual(_parse_tmdb_id("tmdb-550"), 550)

    def test_non_tmdb_slug_returns_none(self) -> None:
        self.assertIsNone(_parse_tmdb_id("assassination"))

    def test_malformed_tmdb_slug_returns_none(self) -> None:
        self.assertIsNone(_parse_tmdb_id("tmdb-abc"))


class CreditsBackfillInteractorTests(unittest.IsolatedAsyncioTestCase):
    def _build(
        self,
        *,
        slugs: list[tuple[int, str]],
        credits_by_tmdb_id: dict[int, TmdbCreditsDto] | None = None,
        fetch_side_effect=None,
    ) -> tuple[CreditsBackfillInteractor, AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
        movies = AsyncMock()
        movies.list_all_slugs.return_value = slugs
        catalog = AsyncMock()
        if fetch_side_effect is not None:
            catalog.fetch_credits.side_effect = fetch_side_effect
        elif credits_by_tmdb_id is not None:
            catalog.fetch_credits.side_effect = lambda tmdb_id: credits_by_tmdb_id[tmdb_id]
        actors = AsyncMock()
        actors.upsert_actor.return_value = 1
        characters = AsyncMock()
        directors = AsyncMock()
        interactor = CreditsBackfillInteractor(
            movies=movies,
            catalog=catalog,
            actors=actors,
            characters=characters,
            directors=directors,
        )
        return interactor, movies, actors, characters, directors

    async def test_skips_non_tmdb_slug(self) -> None:
        interactor, movies, actors, characters, directors = self._build(
            slugs=[(1, "hand-curated-movie")]
        )

        result = await interactor.backfill_credits()

        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.succeeded, 0)
        actors.upsert_actor.assert_not_awaited()

    async def test_upserts_cast_and_directors_for_matched_movie(self) -> None:
        from mova.app.dtos.studio_import_dto import TmdbCastMemberDto, TmdbDirectorDto

        credits = TmdbCreditsDto(
            cast=[TmdbCastMemberDto(tmdb_person_id=100, name="배우A", character="역할1", order=0)],
            directors=[TmdbDirectorDto(tmdb_person_id=200, name="감독A")],
        )
        interactor, movies, actors, characters, directors = self._build(
            slugs=[(1, "tmdb-550")],
            credits_by_tmdb_id={550: credits},
        )

        result = await interactor.backfill_credits()

        self.assertEqual(result.succeeded, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual(actors.upsert_actor.await_count, 2)  # cast 1명 + 감독 1명
        actor_commands = [call.args[0] for call in actors.upsert_actor.await_args_list]
        self.assertIn(100, [c.tmdb_person_id for c in actor_commands])
        self.assertIn(200, [c.tmdb_person_id for c in actor_commands])
        self.assertEqual(
            {c.tmdb_person_id: c.role_type for c in actor_commands},
            {100: "actor", 200: "director"},
        )
        characters.upsert_character.assert_awaited_once()
        directors.upsert_director.assert_awaited_once()

    async def test_one_movie_failure_does_not_block_others(self) -> None:
        from mova.app.dtos.studio_import_dto import TmdbCastMemberDto

        ok_credits = TmdbCreditsDto(
            cast=[TmdbCastMemberDto(tmdb_person_id=1, name="배우A", character="역", order=0)]
        )

        def _side_effect(tmdb_id: int) -> TmdbCreditsDto:
            if tmdb_id == 1:
                raise RuntimeError("TMDB 500")
            return ok_credits

        interactor, movies, actors, characters, directors = self._build(
            slugs=[(1, "tmdb-1"), (2, "tmdb-2")],
            fetch_side_effect=_side_effect,
        )

        result = await interactor.backfill_credits()

        self.assertEqual(result.succeeded, 1)
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.failed_slugs, ["tmdb-1"])

    async def test_all_movies_fail_reports_zero_succeeded(self) -> None:
        interactor, movies, actors, characters, directors = self._build(
            slugs=[(1, "tmdb-1"), (2, "tmdb-2")],
            fetch_side_effect=RuntimeError("TMDB down"),
        )

        result = await interactor.backfill_credits()

        self.assertEqual(result.succeeded, 0)
        self.assertEqual(result.failed, 2)
        self.assertEqual(set(result.failed_slugs), {"tmdb-1", "tmdb-2"})

    async def test_limit_processes_only_first_n(self) -> None:
        interactor, movies, actors, characters, directors = self._build(
            slugs=[(1, "tmdb-1"), (2, "tmdb-2"), (3, "tmdb-3")],
            credits_by_tmdb_id={1: TmdbCreditsDto(), 2: TmdbCreditsDto(), 3: TmdbCreditsDto()},
        )

        result = await interactor.backfill_credits(limit=2)

        self.assertEqual(result.succeeded, 2)
        self.assertEqual(interactor._catalog.fetch_credits.await_count, 2)

    async def test_dry_run_skips_writes(self) -> None:
        from mova.app.dtos.studio_import_dto import TmdbCastMemberDto, TmdbDirectorDto

        credits = TmdbCreditsDto(
            cast=[TmdbCastMemberDto(tmdb_person_id=100, name="배우A", character="역할1", order=0)],
            directors=[TmdbDirectorDto(tmdb_person_id=200, name="감독A")],
        )
        interactor, movies, actors, characters, directors = self._build(
            slugs=[(1, "tmdb-550")],
            credits_by_tmdb_id={550: credits},
        )

        result = await interactor.backfill_credits(dry_run=True)

        self.assertEqual(result.succeeded, 1)
        actors.upsert_actor.assert_not_awaited()
        characters.upsert_character.assert_not_awaited()
        directors.upsert_director.assert_not_awaited()


class ParseArgsTests(unittest.TestCase):
    """scripts/backfill_credits_cli.py --limit/--dry-run 인자 파싱."""

    @classmethod
    def setUpClass(cls) -> None:
        suvisdev_root = ROOT
        if str(suvisdev_root) not in sys.path:
            sys.path.insert(0, str(suvisdev_root))
        from scripts.backfill_credits_cli import _parse_args

        cls._parse_args = staticmethod(_parse_args)

    def test_defaults_are_full_run(self) -> None:
        args = self._parse_args([])
        self.assertIsNone(args.limit)
        self.assertFalse(args.dry_run)

    def test_limit_parses_as_int(self) -> None:
        args = self._parse_args(["--limit", "3"])
        self.assertEqual(args.limit, 3)

    def test_dry_run_flag(self) -> None:
        args = self._parse_args(["--dry-run"])
        self.assertTrue(args.dry_run)

    def test_limit_and_dry_run_combined(self) -> None:
        args = self._parse_args(["--limit", "3", "--dry-run"])
        self.assertEqual(args.limit, 3)
        self.assertTrue(args.dry_run)


if __name__ == "__main__":
    unittest.main()
