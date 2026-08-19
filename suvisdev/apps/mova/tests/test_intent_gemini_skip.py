"""의도 추출 Gemini 호출 절감 — 결정론적 경로로 **실용적으로 강한** 조건이
잡혔을 때만 호출하지 않는다.

`/mova/chat` 1건이 Gemini를 2회(의도 추출 + 추천 생성) 쓰던 것이 분당 15요청
한도에서 "분당 7명"이라는 상한을 만들었다(PROGRESS.md 9순위). 하지만 "장르 하나
만으로도 hard signal"로 봤던 최초 규칙은 "전지현 코미디"류 배우+장르 질의에서
`_guess_actors` 정규식이 조사 없는 이름을 못 잡는 사이 Gemini까지 스킵돼
배우가 통째로 사라지는 결함을 만들었다(QUALITY_PHASE1 §9).

지금 규칙: **배우 이미 잡힘 · 연도 있음 · 국가+장르 조합** 셋 중 하나면 스킵.
"장르만" · "국가만"은 Gemini 폴백을 태워 배우·기타 조건을 보강한다.
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
    """실용적으로 강한 조건이 이미 잡혔을 때만 Gemini 스킵."""

    def setUp(self) -> None:
        self.model = _Model()
        self.svc = IntentExtractionService()

    def _extract(self, message: str) -> dict:
        with patch.object(
            intent_extraction, "get_keymaker", return_value=_Keymaker(self.model)
        ):
            return self.svc.extract(message)

    def test_skips_gemini_when_year_found(self) -> None:
        result = self._extract("2020년대 영화 뭐 볼까")

        self.assertEqual(self.model.calls, 0)
        self.assertEqual(result["search_filters"]["year_min"], 2020)
        self.assertEqual(result["search_filters"]["year_max"], 2029)

    def test_skips_gemini_when_country_and_genre(self) -> None:
        """국가+장르 조합은 강한 필터라 Gemini 스킵."""
        result = self._extract("한국 액션 영화")

        self.assertEqual(self.model.calls, 0)
        filters = result["search_filters"]
        self.assertIn("KR", filters["must"]["countries"])
        self.assertIn("액션", filters["must"]["genres"])

    def test_skips_gemini_when_actor_already_caught(self) -> None:
        """정규식이 배우를 잡았으면 Gemini 재확인 불필요."""
        result = self._extract("송강호 배우 나오는 영화")

        self.assertEqual(self.model.calls, 0)
        self.assertIn("송강호", result["search_filters"]["must"]["actors"])

    def test_country_year_genre_query_still_resolves(self) -> None:
        """PROGRESS.md #9 회귀 케이스 — 이 질의가 하드 조건 3개를 다 잡아야 한다."""
        result = self._extract("2020년대 한국 액션")

        self.assertEqual(self.model.calls, 0)
        filters = result["search_filters"]
        self.assertIn("KR", filters["must"]["countries"])
        self.assertIn("액션", filters["must"]["genres"])
        self.assertEqual((filters["year_min"], filters["year_max"]), (2020, 2029))


class IntentGeminiFallbackTriggerTests(unittest.TestCase):
    """장르만·국가만·무드는 배우 인식 여지가 남아 Gemini 폴백을 태운다
    (QUALITY_PHASE1 §9 — 배우 인식 개선의 대가로 쿼터 소모 증가)."""

    def test_calls_gemini_when_only_genre(self) -> None:
        """배우+장르 질의('전지현 코미디')에서 배우가 정규식에 안 걸리는 상황을
        복구하기 위해, 장르만 잡힌 경우엔 Gemini를 태운다."""
        called: list[str] = []

        class _GenreOnlyModel:
            def generate_content(self, prompt: str) -> object:
                called.append(prompt)

                class _R:
                    text = '{"refined_query": "코미디 추천", "keywords": ["코미디"]}'

                return _R()

        svc = IntentExtractionService()
        with patch.object(
            intent_extraction, "get_keymaker", return_value=_Keymaker(_GenreOnlyModel())
        ):
            result = svc.extract("코미디 영화 추천해줘")

        self.assertEqual(len(called), 1)
        self.assertIn("코미디", result["search_filters"]["must"]["genres"])

    def test_calls_gemini_when_only_country(self) -> None:
        """국가만으로는 배우/장르 판단 불가라 Gemini 태움."""
        called: list[str] = []

        class _CountryOnlyModel:
            def generate_content(self, prompt: str) -> object:
                called.append(prompt)

                class _R:
                    text = '{"refined_query": "한국 영화", "keywords": ["한국"]}'

                return _R()

        svc = IntentExtractionService()
        with patch.object(
            intent_extraction, "get_keymaker", return_value=_Keymaker(_CountryOnlyModel())
        ):
            result = svc.extract("한국 영화 보고 싶어")

        self.assertEqual(len(called), 1)
        self.assertIn("KR", result["search_filters"]["must"]["countries"])


class IntentGeminiStillUsedTests(unittest.TestCase):
    """하드 조건이 없는 무드 질의는 Gemini를 호출하되, refined_query는
    현재 턴 결정론적 결과를 쓴다(이전 턴 컨텍스트 오염 방지)."""

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
        # refined_query는 Gemini 것이 아니라 현재 턴 결정론적 추출 결과
        self.assertIn("볼만한", result["refined_query"])


if __name__ == "__main__":
    unittest.main()
