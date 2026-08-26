"""tmdb_mapper.map_tmdb_row() — original_language 추출 유닛 테스트."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.outbound.http.tmdb_mapper import (  # noqa: E402
    map_kr_certification,
    map_kr_watch_providers,
    map_tmdb_row,
)


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


class MapKrCertificationTests(unittest.TestCase):
    def test_maps_all_grades(self) -> None:
        for raw, expected in [("ALL", "전체"), ("12", "12세"), ("15", "15세"), ("19", "청불")]:
            release_dates = {
                "results": [{"iso_3166_1": "KR", "release_dates": [{"certification": raw}]}]
            }
            self.assertEqual(map_kr_certification(release_dates), expected)

    def test_no_kr_entry_returns_none(self) -> None:
        release_dates = {
            "results": [{"iso_3166_1": "US", "release_dates": [{"certification": "R"}]}]
        }
        self.assertIsNone(map_kr_certification(release_dates))

    def test_unmapped_certification_returns_none(self) -> None:
        release_dates = {
            "results": [{"iso_3166_1": "KR", "release_dates": [{"certification": ""}]}]
        }
        self.assertIsNone(map_kr_certification(release_dates))

    def test_none_input_returns_none(self) -> None:
        self.assertIsNone(map_kr_certification(None))


class MapKrWatchProvidersTests(unittest.TestCase):
    def test_extracts_flatrate_rent_buy_with_shared_link(self) -> None:
        watch_providers = {
            "results": {
                "KR": {
                    "link": "https://example.com/watch",
                    "flatrate": [{"provider_name": "wavve"}],
                    "buy": [{"provider_name": "Google Play Movies"}],
                }
            }
        }

        platforms = map_kr_watch_providers(watch_providers)

        self.assertEqual(
            platforms,
            [
                {"provider": "wavve", "url": "https://example.com/watch", "type": "flatrate"},
                {
                    "provider": "googleplaymovies",
                    "url": "https://example.com/watch",
                    "type": "buy",
                },
            ],
        )

    def test_same_provider_across_kinds_keeps_first_occurrence(self) -> None:
        watch_providers = {
            "results": {
                "KR": {
                    "link": "https://example.com/watch",
                    "flatrate": [{"provider_name": "wavve"}],
                    "buy": [{"provider_name": "wavve"}],
                }
            }
        }

        platforms = map_kr_watch_providers(watch_providers)

        self.assertEqual(len(platforms), 1)
        self.assertEqual(platforms[0]["type"], "flatrate")

    def test_no_kr_entry_returns_empty_list(self) -> None:
        self.assertEqual(map_kr_watch_providers({"results": {}}), [])

    def test_none_input_returns_empty_list(self) -> None:
        self.assertEqual(map_kr_watch_providers(None), [])


class MapTmdbRowAgeRatingPlatformsTests(unittest.TestCase):
    def test_extracts_from_detail_response(self) -> None:
        row = {
            "id": 1,
            "title": "제목",
            "release_dates": {
                "results": [{"iso_3166_1": "KR", "release_dates": [{"certification": "15"}]}]
            },
            "watch/providers": {
                "results": {
                    "KR": {
                        "link": "https://example.com/watch",
                        "flatrate": [{"provider_name": "wavve"}],
                    }
                }
            },
        }

        mapped = map_tmdb_row(row, genre_map={}, poster_url="")

        self.assertEqual(mapped.age_rating, "15세")
        self.assertEqual(
            mapped.platforms,
            [{"provider": "wavve", "url": "https://example.com/watch", "type": "flatrate"}],
        )

    def test_missing_from_list_endpoint_row_defaults_empty(self) -> None:
        """popular/discover 같은 목록 엔드포인트 row엔 이 키 자체가 없다."""
        row = {"id": 1, "title": "제목"}

        mapped = map_tmdb_row(row, genre_map={}, poster_url="")

        self.assertIsNone(mapped.age_rating)
        self.assertEqual(mapped.platforms, [])


if __name__ == "__main__":
    unittest.main()
