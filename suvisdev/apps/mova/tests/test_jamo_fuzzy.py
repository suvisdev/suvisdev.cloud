"""자모 분해 + 퍼지 매칭 단위 테스트."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.domain.value_objects.jamo_fuzzy import (  # noqa: E402
    decompose,
    edit_distance,
    fuzzy_match_titles,
)


class DecomposeTests(unittest.TestCase):
    def test_simple_hangul(self) -> None:
        self.assertEqual(decompose("한"), "ㅎㅏㄴ")

    def test_no_jongseong(self) -> None:
        self.assertEqual(decompose("나"), "ㄴㅏ")

    def test_mixed(self) -> None:
        result = decompose("AB가")
        self.assertEqual(result, "ABㄱㅏ")

    def test_ssang_jamo(self) -> None:
        # 쩸 = ㅉ+ㅔ+ㅁ, 잼 = ㅈ+ㅐ+ㅁ
        self.assertEqual(decompose("쩸"), "ㅉㅔㅁ")
        self.assertEqual(decompose("잼"), "ㅈㅐㅁ")


class EditDistanceTests(unittest.TestCase):
    def test_identical(self) -> None:
        self.assertEqual(edit_distance("abc", "abc"), 0)

    def test_one_sub(self) -> None:
        self.assertEqual(edit_distance("abc", "adc"), 1)

    def test_jamo_typo(self) -> None:
        # 쩸(ㅉㅔㅁ) vs 잼(ㅈㅐㅁ) — 편집거리 2 (ㅉ→ㅈ, ㅔ→ㅐ)
        d = edit_distance(decompose("쩸"), decompose("잼"))
        self.assertEqual(d, 2)


class FuzzyMatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.titles = [
            (1, "더 문"),
            (2, "더 킹"),
            (3, "인셉션"),
            (4, "호프"),
            (5, "라라랜드"),
            (6, "기생충"),
            (7, "더 배트맨"),
        ]

    def test_exact_match_distance_zero(self) -> None:
        results = fuzzy_match_titles("더문", self.titles)
        self.assertTrue(any(mid == 1 for mid, _, _ in results))
        best = results[0]
        self.assertEqual(best[0], 1)  # 더 문
        self.assertEqual(best[2], 0)  # distance 0 (공백 제거 후 동일)

    def test_typo_match(self) -> None:
        # "ㅓ문" → "더문" — 자모 편집거리 1 (ㄷ 누락)
        results = fuzzy_match_titles("ㅓ문", self.titles)
        found_ids = {mid for mid, _, _ in results}
        self.assertIn(1, found_ids)  # 더 문

    def test_similar_titles_both_returned(self) -> None:
        # "더문"은 "더 문"(dist=0)과 "더 킹"(dist≈3)을 모두 반환할 수 있음
        results = fuzzy_match_titles("더문", self.titles)
        self.assertEqual(results[0][0], 1)  # 더 문이 1순위

    def test_no_match_over_threshold(self) -> None:
        results = fuzzy_match_titles("완전다른영화제목", self.titles, max_distance=3)
        self.assertEqual(results, [])

    def test_short_title_strict(self) -> None:
        # "호프" vs "호크" — 편집거리 1이라 매칭됨
        titles = [(1, "호프"), (2, "호크")]
        results = fuzzy_match_titles("호프", titles)
        self.assertEqual(results[0][0], 1)
        self.assertEqual(results[0][2], 0)

    def test_ambiguous_short_titles(self) -> None:
        # "호프"와 "호크" 둘 다 "호ㅍ"에 가까움 → 둘 다 반환
        titles = [(1, "호프"), (2, "호크")]
        results = fuzzy_match_titles("호ㅍ", titles)
        self.assertTrue(len(results) >= 2)


class TitleResolverFuzzyIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """resolve_movie_title의 퍼지 폴백 통합 테스트."""

    async def test_fuzzy_fallback_on_not_found(self) -> None:
        from unittest.mock import AsyncMock

        from mova.adapter.inbound.api.schemas.studio_search_schema import (
            MovaSearchItemSchema,
        )
        from mova.app.use_cases.market_chat_title_resolver import resolve_movie_title

        repo = AsyncMock()
        repo.search_movies_by_title.return_value = []  # exact 0건
        repo.fuzzy_search_movies_by_title.return_value = [
            MovaSearchItemSchema(
                id="1", title="더 문", year="2023", rating=4.0, poster="", match_type="fuzzy"
            )
        ]
        res = await resolve_movie_title(repo, message="더문은 쩸 쓰나", entities=["더문은 쩸 쓰나"])
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.item.title, "더 문")
        repo.fuzzy_search_movies_by_title.assert_awaited_once()

    async def test_no_fuzzy_when_exact_found(self) -> None:
        from unittest.mock import AsyncMock

        from mova.adapter.inbound.api.schemas.studio_search_schema import (
            MovaSearchItemSchema,
        )
        from mova.app.use_cases.market_chat_title_resolver import resolve_movie_title

        repo = AsyncMock()
        repo.search_movies_by_title.return_value = [
            MovaSearchItemSchema(
                id="1", title="호프", year="2021", rating=4.0, poster="", match_type="title"
            )
        ]
        res = await resolve_movie_title(repo, message="호프 어때", entities=["호프"])
        self.assertEqual(res.status, "ok")
        repo.fuzzy_search_movies_by_title.assert_not_awaited()

    async def test_fuzzy_ambiguous_when_multiple(self) -> None:
        from unittest.mock import AsyncMock

        from mova.adapter.inbound.api.schemas.studio_search_schema import (
            MovaSearchItemSchema,
        )
        from mova.app.use_cases.market_chat_title_resolver import resolve_movie_title

        repo = AsyncMock()
        repo.search_movies_by_title.return_value = []
        repo.fuzzy_search_movies_by_title.return_value = [
            MovaSearchItemSchema(
                id="1", title="더 문", year="2023", rating=4.0, poster="", match_type="fuzzy"
            ),
            MovaSearchItemSchema(
                id="2", title="더 킹", year="2022", rating=4.0, poster="", match_type="fuzzy"
            ),
        ]
        res = await resolve_movie_title(repo, message="더뮨 재밌나", entities=[])
        self.assertEqual(res.status, "ambiguous")
        self.assertEqual(len(res.candidates), 2)
