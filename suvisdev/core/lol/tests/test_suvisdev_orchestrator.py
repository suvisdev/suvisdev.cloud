"""generate 요청 본문 조립 — num_ctx를 안 주면 ollama 기본 4096으로 근거가 잘린다(2026-09-27)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lol.suvisdev_orchestrator import SuvisdevOrchestrator  # noqa: E402


class BuildBodyTests(unittest.TestCase):
    def test_options_omitted_when_nothing_set(self) -> None:
        body = SuvisdevOrchestrator(model="m")._build_body(
            "q", system=None, temperature=None, num_ctx=None
        )
        self.assertNotIn("options", body)
        self.assertEqual(body["messages"], [{"role": "user", "content": "q"}])
        self.assertEqual(body["model"], "m")

    def test_temperature_and_num_ctx_go_to_options(self) -> None:
        body = SuvisdevOrchestrator(model="m")._build_body(
            "q", system="s", temperature=0, num_ctx=8192
        )
        self.assertEqual(body["options"], {"temperature": 0, "num_ctx": 8192})
        self.assertEqual(body["messages"][0], {"role": "system", "content": "s"})

    def test_num_ctx_alone(self) -> None:
        body = SuvisdevOrchestrator(model="m")._build_body(
            "q", system=None, temperature=None, num_ctx=4096
        )
        self.assertEqual(body["options"], {"num_ctx": 4096})


class UnderstandJsonTests(unittest.TestCase):
    def test_parses_and_retries_once(self) -> None:
        from unittest.mock import patch

        o = SuvisdevOrchestrator(model="m")
        outputs = iter(["그냥 문장", '{"intent":"booking"}'])
        with patch.object(
            SuvisdevOrchestrator, "generate", side_effect=lambda *a, **k: next(outputs)
        ) as gen:
            self.assertEqual(o.understand_json("q"), {"intent": "booking"})
            self.assertEqual(gen.call_count, 2)
            self.assertTrue(gen.call_args.kwargs["json_format"])

    def test_embedded_object_extracted(self) -> None:
        from unittest.mock import patch

        o = SuvisdevOrchestrator(model="m")
        with patch.object(SuvisdevOrchestrator, "generate", return_value='결과: {"a": 1} 끝'):
            self.assertEqual(o.understand_json("q"), {"a": 1})

    def test_json_format_flag_in_body(self) -> None:
        body = SuvisdevOrchestrator(model="m")._build_body(
            "q", system=None, temperature=None, num_ctx=None, json_format=True
        )
        self.assertEqual(body["format"], "json")


if __name__ == "__main__":
    unittest.main()
