"""리포터(Reporter) — 격상된 VIP/보고서 요청(Case B)을 dispatch 내부에서 직접 종결한다.

공용 오케스트레이터(core/lol)는 exaone3.5:7.8b로 email·spam_filter 등 범용 생성에 쓰이지만,
이 리포터는 빠른 내부 트리아지 응답을 위해 더 가벼운 REPORT_WRITER_MODEL 전용 인스턴스를 쓴다.
"""

from __future__ import annotations

import logging

from core.lol.t1_mid_faker_orchestrator import FakerOrchestratorError, T1MidFakerOrchestrator
from dispatch.app.use_cases.exaone_text_sanitize import sanitize_body
from ontology.domain.events.spoke_events import InboundMessageEvent

logger = logging.getLogger(__name__)

REPORT_WRITER_MODEL = "exaone3.5:2.4b"

_REPORT_SYSTEM = (
    "당신은 전사 ERP 데이터를 취합하는 최고 분석 에이전트입니다. "
    "요청에 대한 간결한 실적 보고서 초안을 한국어로 작성하세요. "
    "불필요한 안내·질문 없이 보고서 본문만 반환하세요."
)


class ReportWriterInteractor:
    """dispatch 내부에서 EXAONE 전용 인스턴스를 호출해 보고서 초안을 작성한다."""

    def __init__(self, *, orchestrator: T1MidFakerOrchestrator) -> None:
        self._orchestrator = orchestrator

    def write(self, event: InboundMessageEvent) -> str:
        logger.info(
            "[dispatch Reporter] 🧠 EXAONE(%s) 호출 — 보고서 초안 생성 착수 | sender=%s",
            REPORT_WRITER_MODEL,
            event.sender,
        )
        try:
            report = sanitize_body(self._orchestrator.generate(event.body, system=_REPORT_SYSTEM))
        except FakerOrchestratorError as e:
            logger.warning(
                "[dispatch Reporter] ⚠️ EXAONE 호출 실패(%s) — 하네스 폴백 보고서로 대체",
                e.detail,
            )
            report = f"[폴백 보고서] '{event.body}' 요청 접수 — EXAONE 미가동 상태"
        logger.info("[dispatch Reporter] ✅ 보고서 생성 완료")
        return report
