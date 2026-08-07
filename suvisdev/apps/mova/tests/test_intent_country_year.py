"""intent_extraction의 국가·연도 추출 — Gemini 없이도 동작해야 한다.

골든셋 #9("2020년대 한국 액션")가 두 사이클 연속 실패한 원인이 인텐트 스키마에
국가·연도 필드가 아예 없었던 것이라(2026-08-07 조사), LLM 응답에 의존하지 않는
결정론적 추출 경로를 고정한다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.outbound.llm.intent_extraction import (  # noqa: E402
    _guess_countries,
    _guess_year_range,
    build_search_filters,
)


class GuessCountriesTests(unittest.TestCase):
    def test_korean_aliases(self) -> None:
        for text in ("한국 영화", "국내 영화 추천", "우리나라 작품"):
            self.assertEqual(_guess_countries(text), ["KR"], text)

    def test_english_speaking_are_distinguished(self) -> None:
        """언어(en)로는 못 가르는 구분 — origin_country를 넣은 이유."""
        self.assertEqual(_guess_countries("영국 영화"), ["GB"])
        self.assertEqual(_guess_countries("미국 영화"), ["US"])

    def test_no_country_mentioned(self) -> None:
        self.assertEqual(_guess_countries("재밌는 액션 영화"), [])


class GuessYearRangeTests(unittest.TestCase):
    def test_four_digit_decade(self) -> None:
        self.assertEqual(_guess_year_range("2020년대 액션"), (2020, 2029))

    def test_two_digit_decade_means_1900s(self) -> None:
        self.assertEqual(_guess_year_range("90년대 로맨스"), (1990, 1999))

    def test_single_year(self) -> None:
        self.assertEqual(_guess_year_range("2015년 영화"), (2015, 2015))

    def test_no_year(self) -> None:
        self.assertEqual(_guess_year_range("액션 영화"), (None, None))


class BuildSearchFiltersTests(unittest.TestCase):
    def test_golden_set_9_shape(self) -> None:
        """LLM 응답이 비어도(parsed={}) 국가·연도·장르가 다 잡혀야 한다."""
        _, filters = build_search_filters("2020년대 한국 액션 영화 추천해줘", [], {})

        self.assertEqual(filters["must"]["countries"], ["KR"])
        self.assertEqual(filters["year_min"], 2020)
        self.assertEqual(filters["year_max"], 2029)
        self.assertIn("액션", filters["must"]["genres"])

    def test_llm_supplied_country_is_kept(self) -> None:
        _, filters = build_search_filters(
            "영화 추천", [], {"must": {"countries": ["GB"], "actors": [], "genres": []}}
        )

        self.assertEqual(filters["must"]["countries"], ["GB"])

    def test_invalid_llm_country_code_is_dropped(self) -> None:
        """LLM이 지어낸 코드를 그대로 쿼리에 넣지 않는다."""
        _, filters = build_search_filters(
            "영화 추천", [], {"must": {"countries": ["ZZ", "korea"], "actors": [], "genres": []}}
        )

        self.assertEqual(filters["must"]["countries"], [])

    def test_no_country_or_year_leaves_empty(self) -> None:
        _, filters = build_search_filters("재밌는 영화", [], {})

        self.assertEqual(filters["must"]["countries"], [])
        self.assertIsNone(filters["year_min"])
        self.assertIsNone(filters["year_max"])


if __name__ == "__main__":
    unittest.main()
