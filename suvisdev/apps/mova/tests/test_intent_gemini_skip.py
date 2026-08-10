"""의도 추출 Gemini 호출 절감 — 결정론적 경로로 충분하면 호출하지 않는다.

`/mova/chat` 1건이 Gemini를 2회(의도 추출 + 추천 생성) 쓰던 것이 분당 15요청
한도에서 "분당 7명"이라는 상한을 만들었다(PROGRESS.md 9순위). 장르·배우·국가·
연도 같은 **하드 조건**이 정규식으로 이미 잡히면 의도 추출은 건너뛴다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.outbound.llm import intent_extraction  # noqa: E402
from mova.adapter.outbound.llm.intent_extraction import (  # noqa: E402
    IntentExtractionService,
)


class _Model:
    def __init__(self) -> None:
        self.calls = 0

    def generate_content(self, prompt: str) -> object:
        self.calls += 1
        raise AssertionError("이 테스트에서 호출되면 안 된다")


class _Keymaker:
    def __init__(self, model: _Model) -> None:
        self._model = model

    def is_gemini_ready(self) -> bool:
        return True

    def get_gemini_model(self, key: object) -> _Model:
        return self._model


class IntentGeminiSkipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = _Model()
        self.svc = IntentExtractionService()

    def _extract(self, message: str) -> dict:
        with patch.object(
            intent_extraction, "get_keymaker", return_value=_Keymaker(self.model)
        ):
            return self.svc.extract(message)

    def test_skips_gemini_when_genre_found(self) -> None:
        result = self._extract("액션 영화 추천해줘")

        self.assertEqual(self.model.calls, 0)
        self.assertIn("액션", result["search_filters"]["must"]["genres"])

    def test_skips_gemini_when_year_found(self) -> None:
        result = self._extract("2020년대 영화 뭐 볼까")

        self.assertEqual(self.model.calls, 0)
        self.assertEqual(result["search_filters"]["year_min"], 2020)
        self.assertEqual(result["search_filters"]["year_max"], 2029)

    def test_skips_gemini_when_country_found(self) -> None:
        result = self._extract("한국 영화 보고 싶어")

        self.assertEqual(self.model.calls, 0)
        self.assertIn("KR", result["search_filters"]["must"]["countries"])

    def test_country_year_genre_query_still_resolves(self) -> None:
        """PROGRESS.md #9 회귀 케이스 — 이 질의가 하드 조건 3개를 다 잡아야 한다."""
        result = self._extract("2020년대 한국 액션")

        self.assertEqual(self.model.calls, 0)
        filters = result["search_filters"]
        self.assertIn("KR", filters["must"]["countries"])
        self.assertIn("액션", filters["must"]["genres"])
        self.assertEqual((filters["year_min"], filters["year_max"]), (2020, 2029))


class IntentGeminiStillUsedTests(unittest.TestCase):
    """하드 조건이 없는 무드 질의는 Gemini를 그대로 쓴다(품질 회귀 방지)."""

    def test_mood_query_calls_gemini(self) -> None:
        called: list[str] = []

        class _MoodModel:
            def generate_content(self, prompt: str) -> object:
                called.append(prompt)

                class _R:
                    text = '{"refined_query": "잔잔한 위로", "keywords": ["위로", "잔잔"]}'

                return _R()

        svc = IntentExtractionService()
        with patch.object(
            intent_extraction, "get_keymaker", return_value=_Keymaker(_MoodModel())
        ):
            result = svc.extract("요즘 너무 지치는데 볼만한 거 없을까")

        self.assertEqual(len(called), 1)
        self.assertEqual(result["refined_query"], "잔잔한 위로")


if __name__ == "__main__":
    unittest.main()
