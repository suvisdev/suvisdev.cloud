"""분류기 destination 5종 확장(2026-08-28 3트랙) — 검증·정규화 경로 고정.

LLM 출력은 fake로 대체한다 — 여기서 고정하는 건 프롬프트 품질이 아니라
"모델이 무엇을 뱉든 destination이 항상 유효한 5종으로 수렴한다"는 계약이다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.llm.qwen_intent_classifier import (  # noqa: E402
    QwenIntentClassifier,
)


def _classifier(raw_response: str) -> QwenIntentClassifier:
    llm = AsyncMock()
    llm.generate.return_value = raw_response
    return QwenIntentClassifier(llm=llm)


class IntentClassifierDestinationTests(unittest.IsolatedAsyncioTestCase):
    async def test_evaluate_destination_passes_through(self) -> None:
        clf = _classifier('{"destination": "evaluate", "entities": ["호프"]}')
        destination, entities = await clf.classify("호프 어때??")
        self.assertEqual(destination, "evaluate")
        self.assertEqual(entities, ["호프"])

    async def test_booking_destination_passes_through(self) -> None:
        clf = _classifier('{"destination": "booking", "entities": ["호프"]}')
        destination, _ = await clf.classify("호프 예매하고 싶어")
        self.assertEqual(destination, "booking")

    async def test_legacy_rag_normalized_to_recommend(self) -> None:
        """구모델·프롬프트 에코가 'rag'를 내도 recommend로 정규화된다."""
        clf = _classifier('{"destination": "rag", "entities": []}')
        destination, _ = await clf.classify("슬픈 영화 추천해줘")
        self.assertEqual(destination, "recommend")

    async def test_unknown_destination_falls_back_to_recommend(self) -> None:
        clf = _classifier('{"destination": "banana", "entities": []}')
        destination, _ = await clf.classify("영화 추천")
        self.assertEqual(destination, "recommend")

    async def test_json_parse_failure_falls_back_to_recommend(self) -> None:
        clf = _classifier("이건 JSON이 아님")
        destination, _ = await clf.classify("영화 추천")
        self.assertEqual(destination, "recommend")

    async def test_meta_complaint_guard_still_routes_general(self) -> None:
        clf = _classifier('{"destination": "recommend", "entities": []}')
        destination, _ = await clf.classify("똑같은 말 반복하지마")
        self.assertEqual(destination, "general")

    async def test_booking_without_booking_vocab_corrected_to_recommend(self) -> None:
        """"최신영화 알려줘" 실사고(2026-09-02): 예매·상영 어휘가 전혀 없는
        질문을 모델이 booking으로 보내면 recommend로 교정한다(결정론 가드) —
        '요즘 상영작 알려줘' 예시와 표면이 비슷해 booking으로 새고, 제목 퍼지
        매칭이 간신/변신/실 같은 무관 후보로 되물었다."""
        clf = _classifier('{"destination": "booking", "entities": []}')
        destination, _ = await clf.classify("최신영화 알려줘")
        self.assertEqual(destination, "recommend")

    async def test_booking_with_showing_vocab_kept(self) -> None:
        clf = _classifier('{"destination": "booking", "entities": []}')
        destination, _ = await clf.classify("요즘 상영작 알려줘")
        self.assertEqual(destination, "booking")

    async def test_booking_with_ticket_vocab_kept(self) -> None:
        clf = _classifier('{"destination": "booking", "entities": ["듄"]}')
        destination, _ = await clf.classify("듄 표 끊고 싶은데")
        self.assertEqual(destination, "booking")


if __name__ == "__main__":
    unittest.main()
