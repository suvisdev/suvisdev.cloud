"""MovieTitle 값 객체·상영작 우선 정책 — 제목 규칙을 한곳에 모은 뒤의 계약(2026-09-27)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "apps") not in sys.path:
    sys.path.insert(0, str(ROOT / "apps"))

from mova.domain.services.showing_title_policy import prefer_showing_year  # noqa: E402
from mova.domain.value_objects.movie_title import MovieTitle, normalize_title  # noqa: E402


class MovieTitleTests(unittest.TestCase):
    def test_equals_ignores_space_and_case(self) -> None:
        self.assertTrue(MovieTitle("더 문").equals("더문"))
        self.assertTrue(MovieTitle("Spider-Man").equals("spider-man"))
        self.assertFalse(MovieTitle("인턴").equals("인턴십"))

    def test_appears_in_ignores_punctuation_and_rejects_short(self) -> None:
        self.assertTrue(
            MovieTitle("스파이더맨: 노 웨이 홈").appears_in("『스파이더맨 노웨이홈』 어때?")
        )
        self.assertFalse(MovieTitle("인턴").appears_in("인턴 어때"))  # 2자 — 오탐 방지
        self.assertTrue(MovieTitle("옵세션").appears_in("옵세션(2026) 상영관을 찾아드릴게요"))

    def test_overlaps_for_box_office_variants(self) -> None:
        self.assertTrue(MovieTitle("인턴").overlaps("인턴: 확장판"))
        self.assertFalse(MovieTitle("").overlaps("인턴"))

    def test_normalize_title(self) -> None:
        self.assertEqual(normalize_title("  A  B "), "ab")


class PreferShowingYearTests(unittest.TestCase):
    def test_box_office_year_wins(self) -> None:
        self.assertEqual(prefer_showing_year(["2015", "2026"], {2026}), "2026")

    def test_newest_when_unknown(self) -> None:
        self.assertEqual(prefer_showing_year(["2015", "2026", None], set()), "2026")

    def test_none_when_no_years(self) -> None:
        self.assertIsNone(prefer_showing_year([None, ""], {2026}))


if __name__ == "__main__":
    unittest.main()
