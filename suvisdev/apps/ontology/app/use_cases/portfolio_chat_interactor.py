"""홈 포트폴리오 채팅 — 매 질문마다 문서 벡터 검색 → 근거 주입 → LLM 생성.

도구 호출 루프를 두지 않는다(EXAONE 3.5 템플릿에 tool 형식이 없고, 답의 근거는 전부 문서에
있다). 근거가 없으면 LLM을 부르지 않고 고정 문구로 답해 지어내기와 비용을 함께 막는다.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeHitDto
from ontology.app.dtos.portfolio_chat_dto import (
    PortfolioChatAnswerDto,
    PortfolioChatCommand,
    PortfolioChatTurn,
)
from ontology.app.ports.input.portfolio_chat_use_case import PortfolioChatUseCase
from ontology.app.ports.output.hub_knowledge_port import HubKnowledgePort
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.knowledge_embedding_port import EmbeddingPort

logger = logging.getLogger(__name__)

SOURCE = "portfolio_doc"
TOP_K = 6
# hub_rag_interactor._MIN_HIT_SCORE와 같은 값·같은 이유(임베딩 공간 불일치 잡음 컷, 2026-08-07 사고).
MIN_HIT_SCORE = 0.15
MAX_HISTORY_TURNS = 6

NO_CONTEXT_REPLY = (
    "제가 가진 자료에서는 그 내용을 찾지 못했어요. Mova·Gildle·ARDA 같은 프로젝트나 "
    "진수택의 경력·기술 스택에 대해 물어봐 주세요."
)

SYSTEM_PROMPT = """당신은 개발자 진수택의 포트폴리오 사이트(suvisdev.cloud) 안내 AI입니다.
규칙:
1. [자료]에 있는 내용만 근거로 답합니다. 자료에 없으면 "자료에서 찾지 못했다"고 말하고 지어내지 않습니다.
2. 개인정보는 이름·학력·경력·기술처럼 자료에 공개된 것만 말합니다. 전화번호·이메일·주소·생년월일은 답하지 않고 "사이트의 Contact 페이지를 참고해 달라"고 안내합니다.
3. 한국어 존댓말로 3~5문장 이내로 간결하게 답합니다. 필요하면 짧은 목록을 씁니다.
4. 자료 제목이나 출처를 답에 붙이지 않습니다."""


def build_prompt(
    hits: Sequence[HubKnowledgeHitDto], history: Sequence[PortfolioChatTurn], message: str
) -> str:
    docs = "\n\n".join(f"### {h.title}\n{h.content}" for h in hits)
    turns = "\n".join(f"{'사용자' if t.role == 'user' else 'AI'}: {t.content}" for t in history)
    return f"[자료]\n{docs}\n\n[대화]\n{turns or '(없음)'}\n\n[질문]\n{message}"


class PortfolioChatInteractor(PortfolioChatUseCase):
    def __init__(
        self, *, repository: HubKnowledgePort, embedding: EmbeddingPort, llm: HubLlmPort
    ) -> None:
        self._repository = repository
        self._embedding = embedding
        self._llm = llm

    async def chat(self, command: PortfolioChatCommand) -> PortfolioChatAnswerDto:
        vector = await self._embedding.embed(command.message)
        raw_hits = await self._repository.search(vector, k=TOP_K, source=SOURCE)
        hits = [h for h in raw_hits if h.score >= MIN_HIT_SCORE]
        logger.info(
            "[PortfolioChat] hits=%d(raw %d) top1=%s score=%.3f",
            len(hits),
            len(raw_hits),
            raw_hits[0].title if raw_hits else "(없음)",
            raw_hits[0].score if raw_hits else 0.0,
        )
        if not hits:
            return PortfolioChatAnswerDto(reply=NO_CONTEXT_REPLY, sources=())

        prompt = build_prompt(hits, command.history[-MAX_HISTORY_TURNS:], command.message)
        reply = await self._llm.generate(prompt, system=SYSTEM_PROMPT)
        sources = tuple(dict.fromkeys(h.title for h in hits))
        return PortfolioChatAnswerDto(reply=reply.strip(), sources=sources)
