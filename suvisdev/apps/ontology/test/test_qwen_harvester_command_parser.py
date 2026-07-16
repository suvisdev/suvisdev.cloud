from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.adapter.outbound.llm.qwen_harvester_command_parser import (  # noqa: E402
    QwenHarvesterCommandParser,
)
from ontology.test.fakes.fake_hub_llm import FakeHubLlm  # noqa: E402


class QwenHarvesterCommandParserTest(unittest.IsolatedAsyncioTestCase):
    async def test_parses_keyword_and_limit_from_json_response(self) -> None:
        llm = FakeHubLlm(response='{"keyword": "패터슨", "limit": 5}')
        parser = QwenHarvesterCommandParser(llm=llm)

        command = await parser.parse("패터슨이란 영화 5개만 가져와줘")

        self.assertEqual(command.keyword, "패터슨")
        self.assertEqual(command.limit, 5)

    async def test_defaults_limit_when_missing(self) -> None:
        llm = FakeHubLlm(response='{"keyword": "박스오피스"}')
        parser = QwenHarvesterCommandParser(llm=llm)

        command = await parser.parse("박스오피스 관련 뉴스 모아줘")

        self.assertEqual(command.limit, 10)

    async def test_falls_back_to_raw_text_on_malformed_json(self) -> None:
        llm = FakeHubLlm(response="죄송해요 이해 못했어요")
        parser = QwenHarvesterCommandParser(llm=llm)

        command = await parser.parse("설국열차 3개")

        self.assertEqual(command.keyword, "설국열차 3개")
        self.assertEqual(command.limit, 10)

    async def test_falls_back_to_raw_text_when_llm_errors(self) -> None:
        llm = FakeHubLlm(raise_error=True)
        parser = QwenHarvesterCommandParser(llm=llm)

        command = await parser.parse("기생충")

        self.assertEqual(command.keyword, "기생충")
        self.assertEqual(command.limit, 10)

    async def test_rejects_translated_keyword_not_in_original_text(self) -> None:
        # 실측 버그: Qwen이 "올드보이"를 "old school"로 번역해버린 사례 재현.
        llm = FakeHubLlm(response='{"keyword": "old school", "limit": 2}')
        parser = QwenHarvesterCommandParser(llm=llm)

        command = await parser.parse("올드보이 영화 정보 2개만")

        self.assertEqual(command.keyword, "올드보이 영화 정보 2개만")

    async def test_limit_is_clamped_to_reasonable_range(self) -> None:
        llm = FakeHubLlm(response='{"keyword": "테스트", "limit": 9999}')
        parser = QwenHarvesterCommandParser(llm=llm)

        command = await parser.parse("테스트 다 가져와줘")

        self.assertEqual(command.limit, 100)


if __name__ == "__main__":
    unittest.main()
