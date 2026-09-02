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

    def test_era_vocab_maps_to_year_max(self) -> None:
        """ "클래식" 실사고(2026-08-28): 시대 어휘가 연도 조건이 안 돼 최신 인기작이
        나왔다 — 명시 연도 없는 시대 어휘는 상한 1999로 근사한다."""
        self.assertEqual(_guess_year_range("클래식 명작 처음 보는 사람용"), (None, 1999))
        self.assertEqual(_guess_year_range("고전 영화 추천"), (None, 1999))

    def test_explicit_decade_wins_over_era_vocab(self) -> None:
        self.assertEqual(_guess_year_range("90년대 클래식 명작"), (1990, 1999))


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

    def test_classic_chip_gets_year_max(self) -> None:
        """제안 칩 원문이 그대로 들어와도 연도 상한이 잡혀 인기작 폴백에서
        recency-first 정렬 대신 클래식이 후보로 남는다."""
        _, filters = build_search_filters("클래식 명작 처음 보는 사람용", [], {})

        self.assertIsNone(filters["year_min"])
        self.assertEqual(filters["year_max"], 1999)

    def test_no_country_or_year_leaves_empty(self) -> None:
        _, filters = build_search_filters("재밌는 영화", [], {})

        self.assertEqual(filters["must"]["countries"], [])
        self.assertIsNone(filters["year_min"])
        self.assertIsNone(filters["year_max"])


class FillerWordBoundaryTests(unittest.TestCase):
    """문두 담화어 제거는 공백이 뒤따를 때만 — \\s*였을 때 "좀비 영화"의 "좀"이
    잘려 "비 영화"(rain)로 RAG·태그 검색이 전부 오염됐다(2026-09-02 실측,
    9/1 "좀비 recs=0" 사고의 진짜 뿌리)."""

    def _extract(self, message: str) -> dict:
        import unittest.mock as m

        from mova.adapter.outbound.llm.intent_extraction import IntentExtractionService

        with m.patch("mova.adapter.outbound.llm.intent_extraction.get_keymaker") as k:
            k.return_value.is_gemini_ready.return_value = False
            return IntentExtractionService().extract(message, [])

    def test_zombie_survives_leading_filler_strip(self) -> None:
        intent = self._extract("좀비 영화 추천해줘")
        self.assertIn("좀비", intent["keywords"])
        self.assertIn("좀비", intent["refined_query"])

    def test_standalone_filler_still_stripped(self) -> None:
        intent = self._extract("좀 신나는 영화 보여줘")
        self.assertNotIn("좀", intent["keywords"])
        self.assertTrue(intent["refined_query"].startswith("신나는"))

    def test_other_leading_fillers_unaffected(self) -> None:
        for message, kept in (
            ("지금 볼만한 스릴러", "스릴러"),
            ("오늘 기분전환용 코미디", "코미디"),
        ):
            intent = self._extract(message)
            self.assertIn(kept, intent["keywords"], message)


if __name__ == "__main__":
    unittest.main()
