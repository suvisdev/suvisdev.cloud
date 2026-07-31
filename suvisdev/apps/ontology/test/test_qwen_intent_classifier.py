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
    _ROUTING_SYSTEM_PROMPT,
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

    async def test_complex_recommendation_phrasing_returns_rag(self) -> None:
        """모델이 few-shot을 따라 올바르게 분류했다고 가정할 때, 복합/이례적
        추천 요청 문구도 rag 튜플을 그대로 통과시키는지 확인한다(파싱 계약 검증 —
        실제 모델의 few-shot 추종 여부까지는 이 유닛 테스트로 보장하지 못한다)."""
        cases = [
            "장르별로 4편씩 추천해줘",
            "가볍게 볼 만한 한국 영화 몇 개 골라줘",
            "주말에 볼 로맨스랑 코미디 하나씩",
            "심각하지 않고 기분 좋아지는 영화",
        ]
        for question in cases:
            with self.subTest(question=question):
                llm = AsyncMock()
                llm.generate.return_value = '{"destination": "rag", "entities": []}'
                classifier = QwenIntentClassifier(llm=llm)

                destination, _ = await classifier.classify(question)

                self.assertEqual(destination, "rag")

    async def test_non_recommendation_fact_query_returns_general(self) -> None:
        """추천이 아닌 단답/사실질의는 general로 남아야 한다(rag와의 대조 케이스)."""
        cases = ["이 영화 감독 누구야?", "줄거리만 알려줘"]
        for question in cases:
            with self.subTest(question=question):
                llm = AsyncMock()
                llm.generate.return_value = '{"destination": "general", "entities": []}'
                classifier = QwenIntentClassifier(llm=llm)

                destination, _ = await classifier.classify(question)

                self.assertEqual(destination, "general")

    def test_routing_prompt_contains_reinforced_few_shot_examples(self) -> None:
        """few-shot 보강이 실제로 프롬프트 문자열에 반영됐는지 확인."""
        required_snippets = [
            "장르별로 4편씩 추천해줘",
            "가볍게 볼 만한 한국 영화 몇 개 골라줘",
            "주말에 볼 로맨스랑 코미디 하나씩",
            "심각하지 않고 기분 좋아지는 영화",
            "이 영화 감독 누구야?",
            "줄거리만 알려줘",
        ]
        for snippet in required_snippets:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, _ROUTING_SYSTEM_PROMPT)

    async def test_unparseable_raw_text_falls_back_to_rag(self) -> None:
        """작은 라우팅 모델이 JSON 대신 질문에 직접 답해버리는 경우 — mova는 추천
        앱이라 애매하면 general(산문 누수)보다 rag(구조화 카드 실패)가 더 안전하다."""
        llm = AsyncMock()
        llm.generate.return_value = "안드레 카파시는 OpenAI와 Tesla에서 일했던 AI 연구자입니다."
        classifier = QwenIntentClassifier(llm=llm)

        destination, entities = await classifier.classify("안드레 카파시가 누구야?")

        self.assertEqual(destination, "rag")
        self.assertEqual(entities, [])

    async def test_llm_call_failure_falls_back_to_rag(self) -> None:
        llm = AsyncMock()
        llm.generate.side_effect = HubRagError(status_code=503, detail="라우터 다운")
        classifier = QwenIntentClassifier(llm=llm)

        destination, entities = await classifier.classify("아무 질문")

        self.assertEqual(destination, "rag")

    async def test_unknown_destination_value_falls_back_to_rag(self) -> None:
        llm = AsyncMock()
        llm.generate.return_value = '{"destination": "unknown_thing", "entities": []}'
        classifier = QwenIntentClassifier(llm=llm)

        destination, _ = await classifier.classify("아무 질문")

        self.assertEqual(destination, "rag")


if __name__ == "__main__":
    unittest.main()
