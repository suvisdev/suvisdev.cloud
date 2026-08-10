"""Gemini 429 재시도 — 분당 한도 창이 넘어가는 순간 걸린 요청 구제.

`_RETRY_SLEEP_SECONDS`만큼 실제로 자면 테스트가 느려지므로 sleep은 패치한다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.outbound.llm import gemini_client  # noqa: E402
from mova.app.ports.output.llm_errors import LLMError  # noqa: E402


class _Response:
    def __init__(self, text: str) -> None:
        self.text = text


class _Model:
    """호출마다 `side_effects`에서 하나씩 꺼내 예외면 raise, 아니면 반환."""

    def __init__(self, *side_effects: object) -> None:
        self._side_effects = list(side_effects)
        self.calls = 0

    def generate_content(self, prompt: str) -> _Response:
        self.calls += 1
        effect = self._side_effects.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return _Response(str(effect))


class _Keymaker:
    def __init__(self, model: _Model) -> None:
        self._model = model

    def is_gemini_ready(self) -> bool:
        return True

    def get_gemini_model(self, key: object) -> _Model:
        return self._model


def _run(model: _Model) -> str:
    with patch.object(gemini_client, "get_keymaker", return_value=_Keymaker(model)):
        with patch.object(gemini_client.time, "sleep"):
            return gemini_client.gemini_reply("안녕", None)


class GeminiQuotaRetryTests(unittest.TestCase):
    def test_retries_once_and_succeeds(self) -> None:
        model = _Model(Exception("429 Quota exceeded"), "두 번째는 성공")

        self.assertEqual(_run(model), "두 번째는 성공")
        self.assertEqual(model.calls, 2)

    def test_raises_429_when_retry_also_fails(self) -> None:
        model = _Model(Exception("429 Quota exceeded"), Exception("429 Quota exceeded"))

        with self.assertRaises(LLMError) as ctx:
            _run(model)

        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("할당량", ctx.exception.detail)
        self.assertEqual(model.calls, 2)

    def test_non_quota_error_is_not_retried(self) -> None:
        """쿼터가 아닌 실패까지 재시도하면 장애 시 부하만 두 배가 된다."""
        model = _Model(Exception("400 Invalid argument"))

        with self.assertRaises(LLMError) as ctx:
            _run(model)

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(model.calls, 1)

    def test_quota_error_detected_case_insensitively(self) -> None:
        model = _Model(Exception("RESOURCE_EXHAUSTED"), "복구")

        self.assertEqual(_run(model), "복구")
        self.assertEqual(model.calls, 2)


if __name__ == "__main__":
    unittest.main()
