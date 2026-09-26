"""generate 요청 본문 조립 — num_ctx를 안 주면 ollama 기본 4096으로 근거가 잘린다(2026-09-27)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lol.t1_mid_faker_orchestrator import T1MidFakerOrchestrator  # noqa: E402


class BuildBodyTests(unittest.TestCase):
    def test_options_omitted_when_nothing_set(self) -> None:
        body = T1MidFakerOrchestrator(model="m")._build_body(
            "q", system=None, temperature=None, num_ctx=None
        )
        self.assertNotIn("options", body)
        self.assertEqual(body["messages"], [{"role": "user", "content": "q"}])
        self.assertEqual(body["model"], "m")

    def test_temperature_and_num_ctx_go_to_options(self) -> None:
        body = T1MidFakerOrchestrator(model="m")._build_body(
            "q", system="s", temperature=0, num_ctx=8192
        )
        self.assertEqual(body["options"], {"temperature": 0, "num_ctx": 8192})
        self.assertEqual(body["messages"][0], {"role": "system", "content": "s"})

    def test_num_ctx_alone(self) -> None:
        body = T1MidFakerOrchestrator(model="m")._build_body(
            "q", system=None, temperature=None, num_ctx=4096
        )
        self.assertEqual(body["options"], {"num_ctx": 4096})


if __name__ == "__main__":
    unittest.main()
