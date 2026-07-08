"""왓슨 트리아지 멀티에이전트 테스트 하네스.

인입(Mock) → Watson(분류) → Holmes 또는 Reporter → Faker(EXAONE) 저니를
콘솔 서사 로그로 추적한다.

실행:
    cd suvisdev
    python -m dispatch.test.harness_watson_triage
"""

from __future__ import annotations

import logging

from core.lol.t1_mid_faker_orchestrator import T1MidFakerOrchestrator
from dispatch.adapter.inbound.watcher.detective_watson_watcher_hub import (
    DetectiveWatsonWatcherHub,
)
from dispatch.app.use_cases.holmes_interactor import HolmesInteractor
from dispatch.app.use_cases.report_writer_interactor import (
    REPORT_WRITER_MODEL,
    ReportWriterInteractor,
)
from ontology.domain.events.spoke_events import InboundMessageEvent


def _build_mock_events() -> list[InboundMessageEvent]:
    """지시사항 1 — 최소 2가지 시나리오 Mock 이벤트."""
    return [
        InboundMessageEvent(
            channel="telegram",
            sender="김대리 (일반 거래처)",
            body="안녕하세요, 지난번 견적 관련해서 간단히 문의드립니다.",
            important_client=False,
        ),
        InboundMessageEvent(
            channel="discord",
            sender="Acme Corp CEO (VIP)",
            body="분기 실적 자동 보고서 발행 요망합니다. 최대한 빨리 부탁드립니다.",
            important_client=True,
        ),
    ]


def _build_watson() -> DetectiveWatsonWatcherHub:
    faker = T1MidFakerOrchestrator(model=REPORT_WRITER_MODEL)
    return DetectiveWatsonWatcherHub(
        holmes=HolmesInteractor(),
        reporter=ReportWriterInteractor(orchestrator=faker),
    )


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    watson = _build_watson()
    for index, event in enumerate(_build_mock_events(), start=1):
        print(f"\n{'=' * 68}")
        print(f"  SCENARIO {index} — {event.channel.upper()} / {event.sender}")
        print(f"{'=' * 68}")
        result = watson.watch(event)
        print(f"[HARNESS] 🏁 최종 산출물:\n  {result}\n")


if __name__ == "__main__":
    run()
