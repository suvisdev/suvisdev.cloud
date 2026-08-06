"""MovieDetailDto.from_orm()/to_schema() — character_name·감독 관통 회귀 테스트.

2026-08-05 mova UI 감사(§4·§5)에서 두 가지가 확인됐다:
1) ActorInMovieSchema에 character_name 필드가 아예 없어 characters.character_name
   (오늘 아침 VARCHAR(50)→TEXT로 고친 그 컬럼) 값이 API 응답까지 도달하지 못했다.
2) 감독은 characters가 아니라 별도 movie_directors 테이블에만 저장되는데
   get_by_slug()가 movie_directors를 조회하지 않아 실 데이터 기준으로 감독이
   상세 응답에 전혀 실리지 않았다(tmdb-1368337 실측: 크리스토퍼 놀란이
   movie_directors엔 있지만 characters엔 없음).

이 테스트는 실 Postgres 없이(SimpleNamespace로 characters/actors/movie_directors
JOIN 결과를 흉내) 두 문제가 고쳐졌는지 DTO/스키마 계층에서 고정한다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.app.dtos.studio_movies_dto import MovieDetailDto  # noqa: E402


def _actor(id: int, name: str, role_type: str) -> SimpleNamespace:
    return SimpleNamespace(id=id, name=name, role_type=role_type, profile_photo_url="")


class MovieDetailDtoActorsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.movie = SimpleNamespace(
            id=1,
            slug="tmdb-1368337",
            title="오디세이",
            release_year=2026,
            rating=8.0,
            poster_url="",
            platforms=[],
            age_rating=None,
            collection_id=None,
            synopsis="신들의 시대, 오디세우스가 고향으로 돌아가는 여정.",
        )
        cast_actor = _actor(id=10, name="박은빈", role_type="actor")
        char = SimpleNamespace(id=100, character_name="은채니")
        director_actor = _actor(id=11, name="크리스토퍼 놀란", role_type="director")

        self.dto = MovieDetailDto.from_orm(
            self.movie,
            char_actor_rows=[(char, cast_actor)],
            tag_rows=[],
            genres=[],
            director_actor_rows=[(SimpleNamespace(), director_actor)],
        )

    def test_cast_member_keeps_character_name(self) -> None:
        cast = next(a for a in self.dto.actors if a.role_type == "actor")
        self.assertEqual(cast.character_name, "은채니")
        self.assertEqual(cast.character_id, 100)

    def test_director_is_included_with_null_character_name(self) -> None:
        director = next(a for a in self.dto.actors if a.role_type == "director")
        self.assertIsNone(director.character_name)
        self.assertIsNone(director.character_id)
        self.assertEqual(director.name, "크리스토퍼 놀란")

    def test_to_schema_carries_character_name_through(self) -> None:
        schema = self.dto.to_schema()
        names = {a.name: a.character_name for a in schema.actors}
        self.assertEqual(names["박은빈"], "은채니")
        self.assertIsNone(names["크리스토퍼 놀란"])

    def test_from_orm_keeps_synopsis(self) -> None:
        self.assertEqual(self.dto.synopsis, "신들의 시대, 오디세우스가 고향으로 돌아가는 여정.")

    def test_to_schema_carries_synopsis_through(self) -> None:
        schema = self.dto.to_schema()
        self.assertEqual(schema.synopsis, "신들의 시대, 오디세우스가 고향으로 돌아가는 여정.")


if __name__ == "__main__":
    unittest.main()
