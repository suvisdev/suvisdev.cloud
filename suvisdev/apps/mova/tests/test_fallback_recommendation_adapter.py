"""추천 폴백 어댑터 — 에러 폴백 + "후보 충분한데 0편" 재시도(2026-09-27)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "apps") not in sys.path:
    sys.path.insert(0, str(ROOT / "apps"))

from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema  # noqa: E402
from mova.adapter.outbound.llm.fallback_recommendation_adapter import (  # noqa: E402
    FallbackRecommendationAdapter,
)
from mova.app.ports.output.llm_errors import LLMError  # noqa: E402


def _item(i: int, match_type: str = "keyword") -> MovaSearchItemSchema:
    return MovaSearchItemSchema(
        id=str(i), title=f"t{i}", year="2020", rating=4.0, poster="", match_type=match_type
    )


def _kwargs(catalog):
    return dict(
        history=[],
        message="법정 드라마 영화",
        intent={},
        tag_catalog=catalog,
        past_intents=[],
        user_nickname=None,
        preferred_genres=[],
        model=None,
    )


class FallbackRecommendationAdapterTests(unittest.IsolatedAsyncioTestCase):
    def _adapter(self, primary_result, fallback_result):
        primary = MagicMock()
        primary.generate_recommendation = AsyncMock(
            side_effect=primary_result if isinstance(primary_result, Exception) else None,
            return_value=None if isinstance(primary_result, Exception) else primary_result,
        )
        fallback = MagicMock()
        fallback.generate_recommendation = AsyncMock(return_value=fallback_result)
        return FallbackRecommendationAdapter(primary, fallback), primary, fallback

    async def test_error_falls_back(self) -> None:
        a, _, fb = self._adapter(LLMError("down"), ("g", ["pick"]))
        self.assertEqual(await a.generate_recommendation(**_kwargs([_item(1)])), ("g", ["pick"]))
        fb.generate_recommendation.assert_awaited_once()

    async def test_zero_picks_with_enough_candidates_retries_fallback(self) -> None:
        a, _, fb = self._adapter(("0편", []), ("g", ["pick"]))
        self.assertEqual(
            await a.generate_recommendation(**_kwargs([_item(i) for i in range(5)])),
            ("g", ["pick"]),
        )
        fb.generate_recommendation.assert_awaited_once()

    async def test_zero_picks_with_few_or_popular_only_candidates_is_honest(self) -> None:
        a, _, fb = self._adapter(("0편", []), ("g", ["pick"]))
        self.assertEqual(
            await a.generate_recommendation(**_kwargs([_item(1), _item(2)])), ("0편", [])
        )
        self.assertEqual(
            await a.generate_recommendation(
                **_kwargs([_item(i, "popular_fallback") for i in range(5)])
            ),
            ("0편", []),
        )
        fb.generate_recommendation.assert_not_awaited()

    async def test_fallback_also_zero_keeps_primary_reply(self) -> None:
        a, _, _ = self._adapter(("0편", []), ("g", []))
        self.assertEqual(
            await a.generate_recommendation(**_kwargs([_item(i) for i in range(4)])), ("0편", [])
        )

    async def test_primary_picks_are_returned_untouched(self) -> None:
        a, _, fb = self._adapter(("p", ["a"]), ("g", ["pick"]))
        self.assertEqual(await a.generate_recommendation(**_kwargs([_item(1)])), ("p", ["a"]))
        fb.generate_recommendation.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
