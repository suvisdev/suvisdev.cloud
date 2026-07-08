"""Hub 이메일 이벤트 기록 — 로그만 찍고 반환하지 않는다."""

from __future__ import annotations

import logging

from ontology.domain.events.spoke_events import DispatchEmailEvent

logger = logging.getLogger(__name__)


class HubEmailOrchestrator:
    def record(self, event: DispatchEmailEvent) -> None:
        logger.info(
            "[ontology Hub] 📨 dispatch 이메일 이벤트 수신 | to=%s subject=%s",
            event.to,
            event.subject,
        )
