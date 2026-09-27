"""자연어 수집 명령 해석기 — HarvesterCommandParserPort 구현체.

어드민 화면에서 "패터슨이란 영화 5개만 가져와줘" 같은 문장을 받아 keyword/limit으로
구조화한다. LlmIntentClassifier와 동일하게 소형 모델 + JSON 스키마 프롬프트 방식을 쓴다.
"""

from __future__ import annotations

import logging

from ontology.adapter.outbound.llm.json_extract import extract_first_json
from ontology.app.dtos.harvester_command_dto import HarvesterCommand
from ontology.app.ports.output.harvester_command_parser_port import HarvesterCommandParserPort
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 10

_SYSTEM_PROMPT = """너는 웹 데이터 수집 도구의 명령 해석기야. 사용자의 자연어 명령에서
검색 키워드와 원하는 수집 개수(limit)를 추출해.
아래 JSON 스키마로만 응답하고, 다른 설명·인사말은 절대 붙이지 마.

출력 스키마:
{"keyword": "핵심 검색어 하나", "limit": 정수}

규칙:
- keyword는 사이트·명령 자체를 가리키는 말(수집해줘, 가져와줘 등)은 빼고 핵심 검색어만.
- keyword는 사용자가 쓴 표기를 절대 번역·의역·순화하지 말고 원문 그대로 옮겨라
  (한글이면 한글 그대로, 영어면 영어 그대로 — 예: "올드보이"를 "old school" 같은
  다른 말로 바꾸지 마라).
- limit이 명시 안 됐으면 10으로 해.

예시:
명령: "패터슨이란 영화 5개만 가져와줘"
답변: {"keyword": "패터슨", "limit": 5}

명령: "올드보이 정보 2개만"
답변: {"keyword": "올드보이", "limit": 2}

명령: "박스오피스 관련 뉴스 모아줘"
답변: {"keyword": "박스오피스", "limit": 10}

명령: "리틀 포레스트 정보 3개"
답변: {"keyword": "리틀 포레스트", "limit": 3}"""


class LlmHarvesterCommandParser(HarvesterCommandParserPort):
    def __init__(self, *, llm: HubLlmPort) -> None:
        self._llm = llm

    async def parse(self, command_text: str) -> HarvesterCommand:
        try:
            raw = await self._llm.generate(command_text, system=_SYSTEM_PROMPT)
        except HubRagError as e:
            logger.warning(
                "[LlmHarvesterCommandParser] 명령 해석 실패, 원문을 키워드로 사용 | detail=%s",
                e.detail,
            )
            return HarvesterCommand(keyword=command_text.strip(), limit=_DEFAULT_LIMIT)

        data = extract_first_json(raw)
        if data is None:
            logger.warning(
                "[LlmHarvesterCommandParser] JSON 파싱 실패, 원문을 키워드로 사용 | raw=%s",
                raw[:200],
            )
            return HarvesterCommand(keyword=command_text.strip(), limit=_DEFAULT_LIMIT)

        keyword = str(data.get("keyword") or command_text).strip()
        if keyword.lower() not in command_text.lower():
            # 소형 모델이 번역·의역해버린 경우(실측: "올드보이"→"old school") — 원문에 없는
            # 말을 지어냈다는 뜻이므로 신뢰하지 않고 명령 원문을 그대로 키워드로 쓴다.
            logger.warning(
                "[LlmHarvesterCommandParser] 원문에 없는 keyword 감지, 원문으로 대체 | "
                "command=%s keyword=%s",
                command_text,
                keyword,
            )
            keyword = command_text.strip()

        try:
            limit = int(data.get("limit") or _DEFAULT_LIMIT)
        except (TypeError, ValueError):
            limit = _DEFAULT_LIMIT
        limit = max(1, min(limit, 100))
        return HarvesterCommand(keyword=keyword, limit=limit)
