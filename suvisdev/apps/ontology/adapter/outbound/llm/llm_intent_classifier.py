"""LLM 기반 시맨틱 인텐트 분류기 — IntentClassifierPort 구현체(HubLlmPort 주입: EXAONE 2.4B, 실패 시 Gemini).
2026-09-27 개명: 구 qwen_intent_classifier/QwenIntentClassifier — 모델은 09-17부터 EXAONE이었다..

semantic_router_interactor(독립 게이트웨이 엔드포인트)와 mova ChatInteractor(실제
채팅)가 이 분류 로직을 공유한다 — 분류 규칙이 두 군데서 따로 놀지 않도록.
"""

from __future__ import annotations

import logging
import re

from ontology.adapter.outbound.llm.json_extract import extract_first_json
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.app.ports.output.intent_classifier_port import IntentClassifierPort

logger = logging.getLogger(__name__)

_DESTINATIONS = ("crud", "recommend", "evaluate", "booking", "general")
# 2026-08-28: mova 재정의(추천·평가·예매)에 따라 rag → recommend/evaluate/booking
# 3종으로 세분화. 구모델 출력·프롬프트 에코로 "rag"가 나오면 recommend로 정규화.
_LEGACY_ALIASES = {"rag": "recommend"}
# 분류 실패(호출 에러·JSON 파싱 실패) 시 general로 보내면 실제 추천 요청이 시스템
# 프롬프트 없는 Gemini 산문으로 새 버린다(2026-07-31 회귀 실측) — mova는 추천 앱이라
# "산문으로 새는 것"보다 "구조화 카드 경로에서 실패하는 것"이 사용자 기대에 가깝다.
_DEFAULT_DESTINATION = "recommend"

# 봇의 직전 행동에 대한 불만·메타 발화 — 추천 파이프라인에 넣으면 빈 카드
# 응답만 반복된다(2026-08-26 프로덕션 zero-rec 실측: "똑같은 말 반복하지마",
# "뭔 영화가 이렇게 없냐", "아니 엄선을 했으면 보여줘야지"). LLM 라우터를
# 거치지 않고 결정론적으로 general로 보낸다. 패턴은 실측 사례 기반으로만
# 유지하고 넓히지 않는다 — "재밌는 영화 없냐"류 추천 요청과 혼동 금지.
_META_COMPLAINT_PATTERNS: tuple[str, ...] = (
    "반복하지",  # "똑같은 말 반복하지마"
    "이렇게 없",  # "뭔 영화가 이렇게 없냐" ("영화 없냐" 단독은 추천 요청이라 제외)
    "보여줘야지",  # "엄선을 했으면 보여줘야지"
)

# 예매 의도 어휘 — 하나도 없는 질문을 모델이 booking으로 보내면 recommend로
# 교정한다("최신영화 알려줘" 실사고 2026-09-02: 프롬프트의 '요즘 상영작 알려줘'
# 예시와 표면이 비슷해 booking으로 새고, 제목 퍼지 매칭이 간신/변신/실 같은
# 무관 후보로 "어떤 작품을 예매하시려나요?" 되물었다).
_BOOKING_VOCAB = re.compile(r"예매|예약|티켓|표\s*끊|상영|극장|영화관|보러|시간표|어디서")

# 추천 확정 어휘 — "추천"·"뭐 있"이 있고 예매·평가 어휘가 없으면 LLM 라우터를
# 건너뛰고 recommend로 확정한다(2026-09-03 속도 개선: 분류기 Gemini 호출이
# E2E 병목 2.06s 실측 — 명백한 추천 질의가 실트래픽의 다수인데 매번 LLM을
# 태울 이유가 없다). 평가·예매 어휘가 섞이면("호프 어때? 추천해줄만해?")
# 기존대로 LLM이 판정한다.
_RECOMMEND_FAST_VOCAB = re.compile(r"추천|뭐\s*있")
_EVALUATE_VOCAB = re.compile(r"어때|볼만|볼 만|평점|평가|재밌(어|나|니)|후기|리뷰|어떤가")

_ROUTING_SYSTEM_PROMPT = """너는 영화를 추천하고, 평가하고, 예매까지 돕는 챗봇 'Mova'의 라우터야. 사용자 질문의 의도를 분류해.
아래 JSON 스키마로만 응답하고, 다른 설명·인사말·예시는 절대 붙이지 마.

출력 스키마:
{"destination": "crud" | "recommend" | "evaluate" | "booking" | "general", "entities": ["질문 속 핵심 키워드"]}

분류 기준 (중요: 영화·시리즈 관련 질문은 전부 recommend/evaluate/booking 중 하나야.
"추천해줘"라는 표현 자체가 잡담이 아니라 recommend를 의미해):
- recommend: 영화·시리즈 추천 요청, 장르·분위기·배우·감독 기반 검색.
  (예: "슬픈 영화 추천해줘", "공포 영화 뭐 있어?", "톰 크루즈 나온 영화 알려줘")
- evaluate: **특정 작품**이 어떤지 평가·평판을 묻는 질문. 작품 제목이 등장하고
  "어때/볼만해/재밌어/평점/평가" 류의 표현이 함께 온다.
  (예: "호프 어때?", "인셉션 볼만해?", "듄 평점 어때?")
- booking: **특정 작품**의 예매·상영관·상영 시간을 묻거나 예매 의사를 밝히는 질문.
  (예: "호프 예매하고 싶어", "인셉션 어디서 상영해?", "듄 표 끊고 싶은데")
  제목이 없어도 "지금 예매/상영 중인 영화"를 찾는 질문은 booking이야
  (예: "지금 예매할 수 있는 영화 뭐 있어?", "요즘 상영작 알려줘").
  단, 예매·상영·극장 표현이 전혀 없이 영화를 소개해 달라는 질문은
  recommend야 ("최신영화 알려줘", "신작 뭐 나왔어"는 recommend).
- crud: 데이터 생성·수정·삭제를 명확히 요구하는 질문 (예: "이 영화 리뷰 삭제해줘")
- general: 영화와 무관한 인사·잡담·일반 상식 (예: "안녕", "오늘 날씨 어때", "너는 누구야")

주의(사람 이름 질문): 사람 이름이 등장한다고 무조건 배우·감독으로 보고 recommend로
보내지 마. "그 사람이 누구야/뭐 하는 사람이야"처럼 인물 자체에 대한 정보를 묻는
질문은 영화와 무관하면 general이야. 그 인물이 나온/만든 "영화"를 명시적으로
찾는 질문일 때만 recommend야.

주의(evaluate vs recommend): "어때"가 있어도 특정 작품 제목이 없으면 evaluate가
아니야. "요즘 코미디 어때?"는 recommend야. evaluate·booking의 entities에는 반드시
작품 제목을 첫 번째로 넣어.

예시:
질문: "슬픈 영화 추천해줘"
답변: {"destination": "recommend", "entities": ["슬픈", "영화"]}

질문: "호프 어때??"
답변: {"destination": "evaluate", "entities": ["호프"]}

질문: "인셉션 볼만해?"
답변: {"destination": "evaluate", "entities": ["인셉션"]}

질문: "호프 예매하고 싶어"
답변: {"destination": "booking", "entities": ["호프"]}

질문: "지금 예매할 수 있는 영화 뭐 있어?"
답변: {"destination": "booking", "entities": []}

질문: "최신영화 알려줘"
답변: {"destination": "recommend", "entities": ["최신", "영화"]}

질문: "듄 어디서 상영해?"
답변: {"destination": "booking", "entities": ["듄"]}

질문: "안녕! 오늘 기분 어때?"
답변: {"destination": "general", "entities": []}

질문: "공포 영화 하나 알려줘"
답변: {"destination": "recommend", "entities": ["공포", "영화"]}

질문: "봉준호가 누구야?"
답변: {"destination": "general", "entities": []}

질문: "봉준호 감독 영화 추천해줘"
답변: {"destination": "recommend", "entities": ["봉준호"]}

질문: "장르별로 4편씩 추천해줘"
답변: {"destination": "recommend", "entities": ["장르별", "4편"]}

질문: "가볍게 볼 만한 한국 영화 몇 개 골라줘"
답변: {"destination": "recommend", "entities": ["가벼운", "한국 영화"]}

질문: "주말에 볼 로맨스랑 코미디 하나씩"
답변: {"destination": "recommend", "entities": ["로맨스", "코미디"]}

질문: "요즘 코미디 어때?"
답변: {"destination": "recommend", "entities": ["코미디"]}

질문: "심각하지 않고 기분 좋아지는 영화"
답변: {"destination": "recommend", "entities": ["기분 좋은"]}

질문: "이 영화 감독 누구야?"
답변: {"destination": "general", "entities": []}

질문: "줄거리만 알려줘"
답변: {"destination": "general", "entities": []}"""


class LlmIntentClassifier(IntentClassifierPort):
    def __init__(self, *, llm: HubLlmPort) -> None:
        self._llm = llm

    async def classify(self, question: str) -> tuple[str, list[str]]:
        if any(p in question for p in _META_COMPLAINT_PATTERNS):
            logger.info("[LlmIntentClassifier] 불만·메타 발화 감지 → general (결정론 가드)")
            return "general", []

        if (
            _RECOMMEND_FAST_VOCAB.search(question)
            and not _BOOKING_VOCAB.search(question)
            and not _EVALUATE_VOCAB.search(question)
        ):
            logger.info("[LlmIntentClassifier] 추천 어휘 감지 → recommend (결정론 가드, LLM 생략)")
            return "recommend", []

        try:
            raw = await self._llm.generate(question, system=_ROUTING_SYSTEM_PROMPT)
        except HubRagError as e:
            logger.warning(
                "[LlmIntentClassifier] 라우팅 호출 실패, %s로 폴백 | detail=%s",
                _DEFAULT_DESTINATION,
                e.detail,
            )
            return _DEFAULT_DESTINATION, []

        data = extract_first_json(raw)
        if data is None:
            logger.warning(
                "[LlmIntentClassifier] 라우팅 JSON 파싱 실패, %s로 폴백 | raw=%s",
                _DEFAULT_DESTINATION,
                raw[:200],
            )
            return _DEFAULT_DESTINATION, []

        raw_dest = data.get("destination")
        destination = (
            _LEGACY_ALIASES.get(str(raw_dest), str(raw_dest)) if raw_dest else _DEFAULT_DESTINATION
        )
        if destination not in _DESTINATIONS:
            destination = _DEFAULT_DESTINATION
        if destination == "booking" and not _BOOKING_VOCAB.search(question):
            logger.info(
                "[LlmIntentClassifier] 예매 어휘 없음 → booking을 recommend로 교정 (결정론 가드)"
            )
            destination = "recommend"
        entities = [str(e) for e in (data.get("entities") or [])]
        return destination, entities
