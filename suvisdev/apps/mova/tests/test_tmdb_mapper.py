"""tmdb_mapper.map_tmdb_row() — original_language 추출 유닛 테스트."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.outbound.http.tmdb_mapper import map_tmdb_row  # noqa: E402


class MapTmdbRowOriginalLanguageTests(unittest.TestCase):
    def test_extracts_original_language(self) -> None:
        row = {"id": 1, "title": "제목", "original_language": "th"}

        mapped = map_tmdb_row(row, genre_map={}, poster_url="")

        self.assertEqual(mapped.original_language, "th")

    def test_normalizes_case(self) -> None:
        row = {"id": 1, "title": "제목", "original_language": "EN"}

        mapped = map_tmdb_row(row, genre_map={}, poster_url="")

        self.assertEqual(mapped.original_language, "en")

    def test_missing_field_defaults_to_empty_string(self) -> None:
        row = {"id": 1, "title": "제목"}

        mapped = map_tmdb_row(row, genre_map={}, poster_url="")

        self.assertEqual(mapped.original_language, "")


class MapTmdbRowOriginCountryTests(unittest.TestCase):
    def test_extracts_country_list(self) -> None:
        """TMDB는 공동제작을 배열로 준다 — 첫 원소만 취하지 않는다."""
        row = {"id": 1, "title": "제목", "origin_country": ["US", "GB"]}

        mapped = map_tmdb_row(row, genre_map={}, poster_url="")

        self.assertEqual(mapped.origin_country, ["US", "GB"])

    def test_normalizes_case_and_drops_blanks(self) -> None:
        row = {"id": 1, "title": "제목", "origin_country": ["kr", "  ", ""]}

        mapped = map_tmdb_row(row, genre_map={}, poster_url="")

        self.assertEqual(mapped.origin_country, ["KR"])

    def test_missing_field_defaults_to_empty_list(self) -> None:
        row = {"id": 1, "title": "제목"}

        mapped = map_tmdb_row(row, genre_map={}, poster_url="")

        self.assertEqual(mapped.origin_country, [])


if __name__ == "__main__":
    unittest.main()
