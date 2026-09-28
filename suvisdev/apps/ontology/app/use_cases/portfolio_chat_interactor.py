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
# 진수택 본인 프로필 청크는 검색 순위와 무관하게 상위 2개를 근거에 넣는다. ARDA(채용 ATS) 지킬이
# "지원자 학력·이력서" 청크를 많이 갖고 있어 "학력이 어떻게 돼"에서 프로필이 밀려났다(2026-09-28).
PROFILE_REF_PREFIX = "portfolio:profile#"
PROFILE_KEEP = 2
_SEARCH_POOL = 30

NO_CONTEXT_REPLY = (
    "저는 Suvisdev예요. 제가 가진 자료에서는 그 내용을 찾지 못했어요. Mova·Gildle·ARDA 같은 "
    "프로젝트나 진수택의 경력·기술 스택에 대해 물어봐 주세요."
)

# 범위 밖 질문 표식 — 모델이 이것만 출력하면 고정 거절 문구로 바꾼다. 검색 점수로는 가를 수 없었다
# (2026-09-28 실측: "오늘 날씨"·"김치찌개 레시피" top1 0.31~0.51, "학력"·"mova" 0.41~0.64로 겹침).
OUT_OF_SCOPE_MARK = "[범위밖]"
OUT_OF_SCOPE_REPLY = (
    "저는 진수택과 그가 만든 프로젝트(Mova·Gildle·약속·ARDA), 이 사이트에 대한 질문에만 답하고 있어요. "
    "경력·기술 스택·프로젝트에 대해 물어봐 주세요."
)

SYSTEM_PROMPT = """당신의 이름은 Suvisdev(수비스데브)입니다. 개발자 진수택이 만든 포트폴리오 사이트(suvisdev.cloud)의 \
AI 비서로, 이름은 진수택의 '수'와 아이언맨의 AI 비서 자비스(JARVIS)의 '비스'를 합친 것입니다. 자신을 소개할 때는 \
"Suvisdev"라고 하고, 자비스처럼 차분하고 정중하되 딱딱하지 않게 말합니다.
규칙:
0. 먼저 [질문]이 답할 범위인지 판단합니다. 범위는 진수택(경력·학력·기술·연락 안내), 그의 프로젝트(Mova·Gildle·약속·ARDA 등)와 개발 과정, 이 사이트(suvisdev.cloud), 그리고 Suvisdev 자신에 대한 인사·소개뿐입니다. 일반 상식·시사·날씨·요리·코딩 대행·수학·다른 사람·다른 회사 등 범위 밖이면 다른 말 없이 정확히 "[범위밖]"만 출력합니다.
1. [자료]에 있는 내용만 근거로 답합니다. 자료에 없으면 "자료에서 찾지 못했다"고 말하고 지어내지 않습니다.
2. 개인정보는 이름·학력·경력·기술처럼 자료에 공개된 것만 말합니다. 전화번호·이메일·주소·생년월일은 답하지 않고 "사이트의 Contact 페이지를 참고해 달라"고 안내합니다.
3. 한국어 존댓말로 3~5문장 이내로 간결하게 답합니다. 필요하면 짧은 목록을 씁니다.
4. 자료 제목이나 출처를 답에 붙이지 않습니다.
5. 서식은 **굵게**, 글머리 목록(- ), 번호 목록(1. ), 링크([이름](URL))만 씁니다. 표·제목(#)·코드 블록·이미지는 쓰지 않습니다."""


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
        pool = await self._repository.search(vector, k=_SEARCH_POOL, source=SOURCE)
        raw_hits = pool[:TOP_K]
        hits = [h for h in raw_hits if h.score >= MIN_HIT_SCORE]
        if hits:
            have = {h.source_ref for h in hits}
            profile = [
                h
                for h in pool
                if h.source_ref.startswith(PROFILE_REF_PREFIX) and h.source_ref not in have
            ][: max(0, PROFILE_KEEP - sum(r.startswith(PROFILE_REF_PREFIX) for r in have))]
            hits = profile + hits
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
        reply = (await self._llm.generate(prompt, system=SYSTEM_PROMPT)).strip()
        if OUT_OF_SCOPE_MARK in reply:
            logger.info("[PortfolioChat] 범위 밖 질문 거절")
            return PortfolioChatAnswerDto(reply=OUT_OF_SCOPE_REPLY, sources=())
        sources = tuple(dict.fromkeys(h.title for h in hits))
        return PortfolioChatAnswerDto(reply=reply, sources=sources)
