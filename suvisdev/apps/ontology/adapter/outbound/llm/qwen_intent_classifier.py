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
# 분류 실패(호출 에러·JSON 파싱 실패) 시 general로 보내면 실제 추천 요청이 시스템
# 프롬프트 없는 Gemini 산문으로 새 버린다(2026-07-31 회귀 실측) — mova는 추천 앱이라
# "산문으로 새는 것"보다 "구조화 카드 경로에서 실패하는 것"이 사용자 기대에 가깝다.
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

주의(사람 이름 질문): 사람 이름이 등장한다고 무조건 배우·감독으로 보고 rag로
보내지 마. "그 사람이 누구야/뭐 하는 사람이야"처럼 인물 자체에 대한 정보를 묻는
질문은 영화와 무관하면 general이야. 그 인물이 나온/만든 "영화"를 명시적으로
찾는 질문일 때만 rag야.

예시:
질문: "슬픈 영화 추천해줘"
답변: {"destination": "rag", "entities": ["슬픈", "영화"]}

질문: "안녕! 오늘 기분 어때?"
답변: {"destination": "general", "entities": []}

질문: "공포 영화 하나 알려줘"
답변: {"destination": "rag", "entities": ["공포", "영화"]}

질문: "안드레 카파시가 누구야?"
답변: {"destination": "general", "entities": []}

질문: "봉준호가 누구야?"
답변: {"destination": "general", "entities": []}

질문: "봉준호 감독 영화 추천해줘"
답변: {"destination": "rag", "entities": ["봉준호"]}

질문: "장르별로 4편씩 추천해줘"
답변: {"destination": "rag", "entities": ["장르별", "4편"]}

질문: "가볍게 볼 만한 한국 영화 몇 개 골라줘"
답변: {"destination": "rag", "entities": ["가벼운", "한국 영화"]}

질문: "주말에 볼 로맨스랑 코미디 하나씩"
답변: {"destination": "rag", "entities": ["로맨스", "코미디"]}

질문: "심각하지 않고 기분 좋아지는 영화"
답변: {"destination": "rag", "entities": ["기분 좋은"]}

질문: "이 영화 감독 누구야?"
답변: {"destination": "general", "entities": []}

질문: "줄거리만 알려줘"
답변: {"destination": "general", "entities": []}"""


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
