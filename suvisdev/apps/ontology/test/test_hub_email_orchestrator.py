from __future__ import annotations

import logging
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.app.use_cases.hub_email_orchestrator import HubEmailOrchestrator  # noqa: E402
from ontology.domain.events.spoke_events import DispatchEmailEvent  # noqa: E402


class HubEmailOrchestratorTest(unittest.TestCase):
    def test_record_emits_log(self) -> None:
        hub = HubEmailOrchestrator()
        event = DispatchEmailEvent(to="user@example.com", prompt="p", subject="제목")

        with self.assertLogs(
            "ontology.app.use_cases.hub_email_orchestrator", level=logging.INFO
        ) as cm:
            hub.record(event)

        self.assertTrue(
            any("[ontology Hub]" in line and "user@example.com" in line for line in cm.output),
            msg=f"기대 로그 없음: {cm.output}",
        )

    def test_record_log_includes_subject(self) -> None:
        hub = HubEmailOrchestrator()
        event = DispatchEmailEvent(to="x@y.com", prompt="p", subject="중요 공지")

        with self.assertLogs(
            "ontology.app.use_cases.hub_email_orchestrator", level=logging.INFO
        ) as cm:
            hub.record(event)

        self.assertTrue(any("중요 공지" in line for line in cm.output))

    def test_record_subject_none(self) -> None:
        hub = HubEmailOrchestrator()
        event = DispatchEmailEvent(to="a@b.com", prompt="p", subject=None)

        with self.assertLogs("ontology.app.use_cases.hub_email_orchestrator", level=logging.INFO):
            result = hub.record(event)

        self.assertIsNone(result)

    def test_record_returns_none(self) -> None:
        hub = HubEmailOrchestrator()
        event = DispatchEmailEvent(to="a@b.com", prompt="p", subject="s")

        with self.assertLogs("ontology.app.use_cases.hub_email_orchestrator", level=logging.INFO):
            result = hub.record(event)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
