"""의도 추출은 Gemini를 호출하지 않는다 — 전 질의 유형 결정론 단독(2026-09-11).

역사: "실용적으로 강한 조건(배우·연도·국가+장르)이면 스킵, 장르만·국가만·
무드는 Gemini로 배우를 보강"하는 규칙이 있었다(QUALITY_PHASE1 §9). 그러나
08-19 멀티턴 오염 수정 2건(f59f1d4·5c9c24c)이 Gemini 산출물을 전부 결정론
결과로 덮으면서 호출만 남고 결과는 사용되지 않는 상태가 됐고, 429 재시도
지연(3.7~5s)의 원인이기만 했다. 2026-09-11 호출 자체를 제거 — 이 파일은
"어떤 질의 유형에서도 keymaker/Gemini에 손대지 않고 결정론 추출이 성립한다"를
고정한다. 배우 보강을 재도입하려면 현재 턴만 Gemini에 주고 must.actors만
병합하는 별도 설계가 필요하다(무단 복원 금지).
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

from mova.adapter.outbound.llm.intent_extraction import (  # noqa: E402
    IntentExtractionService,
)


def _extract(message: str, history: list[dict[str, str]] | None = None) -> dict:
    """keymaker가 어디서든 조회되면 즉시 실패 — 네트워크·키 의존 0을 보장."""
    with patch(
        "core.matrix.vauly_keymaker_secret_manager.get_keymaker",
        side_effect=AssertionError("의도 추출은 keymaker/Gemini를 쓰면 안 된다"),
    ):
        return IntentExtractionService().extract(message, history)


class IntentDeterministicOnlyTests(unittest.TestCase):
    """이전 스킵 규칙의 양쪽 분기(스킵 대상 / Gemini 폴백 대상) 전부 결정론 단독."""

    def test_year_query(self) -> None:
        result = _extract("2020년대 영화 뭐 볼까")
        self.assertEqual(result["search_filters"]["year_min"], 2020)
        self.assertEqual(result["search_filters"]["year_max"], 2029)

    def test_country_and_genre_query(self) -> None:
        filters = _extract("한국 액션 영화")["search_filters"]
        self.assertIn("KR", filters["must"]["countries"])
        self.assertIn("액션", filters["must"]["genres"])

    def test_actor_query(self) -> None:
        result = _extract("송강호 배우 나오는 영화")
        self.assertIn("송강호", result["search_filters"]["must"]["actors"])

    def test_country_year_genre_query(self) -> None:
        """PROGRESS.md #9 회귀 케이스 — 하드 조건 3개를 다 잡아야 한다."""
        filters = _extract("2020년대 한국 액션")["search_filters"]
        self.assertIn("KR", filters["must"]["countries"])
        self.assertIn("액션", filters["must"]["genres"])
        self.assertEqual((filters["year_min"], filters["year_max"]), (2020, 2029))

    def test_genre_only_query(self) -> None:
        """구 규칙에선 Gemini 폴백 대상이던 질의도 결정론 단독으로 성립."""
        result = _extract("코미디 영화 추천해줘")
        self.assertIn("코미디", result["search_filters"]["must"]["genres"])

    def test_country_only_query(self) -> None:
        result = _extract("한국 영화 보고 싶어")
        self.assertIn("KR", result["search_filters"]["must"]["countries"])

    def test_mood_query(self) -> None:
        """무드 질의 — refined_query는 현재 턴 결정론 결과."""
        result = _extract("요즘 너무 지치는데 볼만한 거 없을까")
        self.assertIn("볼만한", result["refined_query"])

    def test_history_does_not_pollute_current_turn(self) -> None:
        """08-19 수정의 핵심 불변식 — 이전 턴 장르가 현재 턴 필터에 잔존하지 않는다."""
        history = [{"role": "user", "content": "액션 영화 추천해줘"}]
        filters = _extract("여행 영화 추천해줘", history)["search_filters"]
        self.assertNotIn("액션", filters["must"]["genres"])


if __name__ == "__main__":
    unittest.main()
