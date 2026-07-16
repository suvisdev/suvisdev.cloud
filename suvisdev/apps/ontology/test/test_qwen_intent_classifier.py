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
from ontology.app.ports.output.hub_rag_errors import HubRagError  # noqa: E402


class QwenIntentClassifierTests(unittest.IsolatedAsyncioTestCase):
    async def test_valid_json_returns_classified_destination(self) -> None:
        llm = AsyncMock()
        llm.generate.return_value = '{"destination": "rag", "entities": ["공포", "영화"]}'
        classifier = QwenIntentClassifier(llm=llm)

        destination, entities = await classifier.classify("공포 영화 추천해줘")

        self.assertEqual(destination, "rag")
        self.assertEqual(entities, ["공포", "영화"])

    async def test_unparseable_raw_text_falls_back_to_general(self) -> None:
        """작은 라우팅 모델이 JSON 대신 질문에 직접 답해버리는 경우 —
        영화와 무관한 질문을 rag(영화 추천)로 잘못 보내면 안 된다."""
        llm = AsyncMock()
        llm.generate.return_value = "안드레 카파시는 OpenAI와 Tesla에서 일했던 AI 연구자입니다."
        classifier = QwenIntentClassifier(llm=llm)

        destination, entities = await classifier.classify("안드레 카파시가 누구야?")

        self.assertEqual(destination, "general")
        self.assertEqual(entities, [])

    async def test_llm_call_failure_falls_back_to_general(self) -> None:
        llm = AsyncMock()
        llm.generate.side_effect = HubRagError(status_code=503, detail="라우터 다운")
        classifier = QwenIntentClassifier(llm=llm)

        destination, entities = await classifier.classify("아무 질문")

        self.assertEqual(destination, "general")

    async def test_unknown_destination_value_falls_back_to_general(self) -> None:
        llm = AsyncMock()
        llm.generate.return_value = '{"destination": "unknown_thing", "entities": []}'
        classifier = QwenIntentClassifier(llm=llm)

        destination, _ = await classifier.classify("아무 질문")

        self.assertEqual(destination, "general")


if __name__ == "__main__":
    unittest.main()
