"""시맨틱 인텐트 게이트웨이 — 질문 1건을 crud/rag/general 세 갈래로 분류해 처리한다.

QLoRA 파인튜닝은 필요 없다. 단일 모델(Qwen2.5-1.5B, ontology/adapter/outbound/llm/
qwen_llm_adapter.py)에 역할별 시스템 프롬프트만 갈아 끼우는 동적 프롬프팅으로
분류(routing)·RAG 답변 두 역할을 겸한다 — VRAM을 추가로 쓰지 않고, PoC 단계에서
파인튜닝 데이터셋을 만들 필요 없이 프롬프트 수정만으로 반복 검증할 수 있다.

- crud: 결정론적 분기 — 실제 CRUD 실행은 각 Spoke 책임이라 여기서는 위임 안내만 반환.
- rag: HubRagUseCase로 hub_knowledge 검색 → 근거(Context)를 시스템 프롬프트에 박아
  같은 Qwen 모델로 grounded 답변 생성. 근거가 없으면 추측하지 않고 바로 안내한다.
- general: 지식 조회가 필요 없는 잡담 — 기존 MycroftUseCase(Gemini)에 위임한다.
"""

from __future__ import annotations

import json
import logging

from ontology.app.dtos.mycroft_dto import MycroftAskCommand
from ontology.app.dtos.semantic_router_dto import SemanticRouteCommand, SemanticRouteDto
from ontology.app.ports.input.hub_rag_use_case import HubRagUseCase
from ontology.app.ports.input.mycroft_use_case import MycroftUseCase
from ontology.app.ports.input.semantic_router_use_case import SemanticRouterUseCase
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError

logger = logging.getLogger(__name__)

_DESTINATIONS = ("crud", "rag", "general")
_DEFAULT_DESTINATION = "rag"

_ROUTING_SYSTEM_PROMPT = """너는 사용자 질문의 의도를 분류하는 라우터야.
아래 JSON 스키마로만 응답하고, 다른 설명·인사말·예시는 절대 붙이지 마.

출력 스키마:
{"destination": "crud" | "rag" | "general", "entities": ["질문 속 핵심 키워드"]}

분류 기준:
- crud: 데이터 생성·수정·삭제를 명확히 요구하는 질문
- rag: 저장된 지식(온톨로지 Hub)에서 사실을 찾아 답해야 하는 질문
- general: 인사·잡담·일반 상식 등 별도 지식 조회가 필요 없는 질문

예시:
질문: "슬픈 영화 추천해줘"
답변: {"destination": "rag", "entities": ["슬픈", "영화"]}"""

_RAG_SYSTEM_PROMPT_TEMPLATE = """너는 온톨로지 Hub에 저장된 지식에만 기반해 사실을 전달하는 AI 비서야.
반드시 아래 [Context] 안의 정보만 사용해서 답해. [Context]에 없는 내용을 추측하거나
지어내는 것은 절대 허용되지 않아.

[Context]
{context}"""


def _extract_first_json(raw: str) -> dict | None:
    """소형 모델은 JSON 뒤에 부연설명을 덧붙이는 경우가 있어(EXAONE AWQ에서 실측),
    첫 `{`부터 그리디하게 긁지 않고 첫 번째로 완결되는 JSON 객체 하나만 추출한다."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = text.find("{")
    if start == -1:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(text, start)
        return data
    except json.JSONDecodeError:
        return None


class SemanticRouterInteractor(SemanticRouterUseCase):
    def __init__(
        self,
        *,
        router_llm: HubLlmPort,
        rag: HubRagUseCase,
        general: MycroftUseCase,
    ) -> None:
        self._router_llm = router_llm
        self._rag = rag
        self._general = general

    async def route(self, command: SemanticRouteCommand) -> SemanticRouteDto:
        destination, entities = await self._classify(command.question)
        logger.info(
            "[SemanticRouterInteractor] destination=%s entities=%s", destination, entities
        )

        if destination == "crud":
            return SemanticRouteDto(
                destination="crud",
                entities=entities,
                answer=f"[CRUD 위임] {', '.join(entities) or command.question}",
            )

        if destination == "general":
            answer = await self._general.ask(MycroftAskCommand(question=command.question))
            return SemanticRouteDto(destination="general", entities=entities, answer=answer.text)

        return await self._answer_with_rag(command.question, entities)

    async def _classify(self, question: str) -> tuple[str, list[str]]:
        try:
            raw = await self._router_llm.generate(question, system=_ROUTING_SYSTEM_PROMPT)
        except HubRagError as e:
            logger.warning(
                "[SemanticRouterInteractor] 라우팅 호출 실패, %s로 폴백 | detail=%s",
                _DEFAULT_DESTINATION,
                e.detail,
            )
            return _DEFAULT_DESTINATION, []

        data = _extract_first_json(raw)
        if data is None:
            logger.warning(
                "[SemanticRouterInteractor] 라우팅 JSON 파싱 실패, %s로 폴백 | raw=%s",
                _DEFAULT_DESTINATION,
                raw[:200],
            )
            return _DEFAULT_DESTINATION, []

        destination = data.get("destination")
        if destination not in _DESTINATIONS:
            destination = _DEFAULT_DESTINATION
        entities = [str(e) for e in (data.get("entities") or [])]
        return destination, entities

    async def _answer_with_rag(self, question: str, entities: list[str]) -> SemanticRouteDto:
        # 현재 HubRagUseCase.search_movies는 mova_movie 소스로 한정돼 있다
        # (범용 온톨로지 검색으로 넓히는 건 이번 스코프 밖).
        hits = await self._rag.search_movies(question)
        if not hits:
            return SemanticRouteDto(
                destination="rag",
                entities=entities,
                answer=(
                    f"죄송합니다. 관련 정보를 온톨로지 Hub에서 찾을 수 없습니다. "
                    f"(키워드: {', '.join(entities) or '없음'})"
                ),
            )

        context = "\n".join(f"- {hit.title}: {hit.content}" for hit in hits)
        system = _RAG_SYSTEM_PROMPT_TEMPLATE.format(context=context)
        try:
            answer = await self._router_llm.generate(question, system=system)
        except HubRagError as e:
            return SemanticRouteDto(
                destination="rag",
                entities=entities,
                answer=f"답변 생성에 실패했습니다: {e.detail}",
            )
        return SemanticRouteDto(destination="rag", entities=entities, answer=answer)
