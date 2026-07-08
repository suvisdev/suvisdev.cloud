"""홈즈(Holmes) — 일반 업무(Case A)를 스포크 내부에서 자체 종결 처리."""

from __future__ import annotations

import logging

from ontology.domain.events.spoke_events import InboundMessageEvent

logger = logging.getLogger(__name__)


class HolmesInteractor:
    """중요도 낮은 인바운드 메시지를 dispatch 내부에서 소화·종결한다."""

    def resolve(self, event: InboundMessageEvent) -> str:
        logger.info(
            "[dispatch Holmes] 🕵️ 일반 업무 자체 처리 | %s <%s>",
            event.channel,
            event.sender,
        )
        resolution = f"'{event.body}' 문의에 표준 응대 완료"
        logger.info("[dispatch Holmes] ✅ 종결: %s", resolution)
        return resolution
