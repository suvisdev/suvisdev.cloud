"""Qwen2.5-1.5B 기반 시맨틱 인텐트 분류기 — IntentClassifierPort 구현체.

semantic_router_interactor(독립 게이트웨이 엔드포인트)와 mova ChatInteractor(실제
채팅)가 이 분류 로직을 공유한다 — 분류 규칙이 두 군데서 따로 놀지 않도록.
"""

from __future__ import annotations

import logging

from ontology.adapter.outbound.llm.json_extract import extract_first_json
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.app.ports.output.intent_classifier_port import IntentClassifierPort

logger = logging.getLogger(__name__)

_DESTINATIONS = ("crud", "rag", "general")
_DEFAULT_DESTINATION = "rag"

_ROUTING_SYSTEM_PROMPT = """너는 영화 추천 챗봇 'Mova'의 라우터야. 사용자 질문의 의도를 분류해.
아래 JSON 스키마로만 응답하고, 다른 설명·인사말·예시는 절대 붙이지 마.

출력 스키마:
{"destination": "crud" | "rag" | "general", "entities": ["질문 속 핵심 키워드"]}

분류 기준 (중요: 영화·시리즈 추천/검색/정보 요청은 전부 "rag"야. "추천해줘"라는
표현 자체가 잡담이 아니라 rag를 의미해):
- rag: 영화·시리즈 추천 요청, 특정 장르·분위기·배우·감독 기반 검색, 특정 작품에 대한
  질문 등 영화 콘텐츠와 관련된 모든 질문. (예: "슬픈 영화 추천해줘", "공포 영화 뭐 있어?",
  "톰 크루즈 나온 영화 알려줘")
- crud: 데이터 생성·수정·삭제를 명확히 요구하는 질문 (예: "이 영화 리뷰 삭제해줘")
- general: 영화와 무관한 인사·잡담·일반 상식 (예: "안녕", "오늘 날씨 어때", "너는 누구야")

예시:
질문: "슬픈 영화 추천해줘"
답변: {"destination": "rag", "entities": ["슬픈", "영화"]}

질문: "안녕! 오늘 기분 어때?"
답변: {"destination": "general", "entities": []}

질문: "공포 영화 하나 알려줘"
답변: {"destination": "rag", "entities": ["공포", "영화"]}"""


class QwenIntentClassifier(IntentClassifierPort):
    def __init__(self, *, llm: HubLlmPort) -> None:
        self._llm = llm

    async def classify(self, question: str) -> tuple[str, list[str]]:
        try:
            raw = await self._llm.generate(question, system=_ROUTING_SYSTEM_PROMPT)
        except HubRagError as e:
            logger.warning(
                "[QwenIntentClassifier] 라우팅 호출 실패, %s로 폴백 | detail=%s",
                _DEFAULT_DESTINATION,
                e.detail,
            )
            return _DEFAULT_DESTINATION, []

        data = extract_first_json(raw)
        if data is None:
            logger.warning(
                "[QwenIntentClassifier] 라우팅 JSON 파싱 실패, %s로 폴백 | raw=%s",
                _DEFAULT_DESTINATION,
                raw[:200],
            )
            return _DEFAULT_DESTINATION, []

        destination = data.get("destination")
        if destination not in _DESTINATIONS:
            destination = _DEFAULT_DESTINATION
        entities = [str(e) for e in (data.get("entities") or [])]
        return destination, entities
