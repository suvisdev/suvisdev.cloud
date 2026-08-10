from __future__ import annotations

import logging
import time
from typing import Literal

from core.matrix.vauly_keymaker_secret_manager import get_keymaker
from mova.app.ports.output.llm_errors import LLMError, LLMUnavailableError

logger = logging.getLogger(__name__)

# 분당 한도(무료 티어 15요청)는 고정 윈도우라, 창이 막 넘어가는 순간에 걸린
# 요청은 짧게 기다렸다 다시 쏘면 통과한다. 하루 한도(임베딩 1000건 등)에
# 걸린 경우엔 몇 초 기다려도 소용없으므로 재시도는 1회로 끝낸다 —
# 사용자를 40초씩 붙잡아 두지 않기 위해서다.
_RETRY_SLEEP_SECONDS = 2.0


def _is_quota_error(err: str) -> bool:
    low = err.lower()
    return "429" in err or "quota" in low or "resource_exhausted" in low


def gemini_reply(prompt: str, model_key: Literal["flash", "flash15", "pro"] | None) -> str:
    keymaker = get_keymaker()
    if not keymaker.is_gemini_ready():
        raise LLMUnavailableError(
            "GEMINI_API_KEY가 설정되지 않았습니다. suvisdev/.env 에 키를 설정하세요."
        )
    gemini = keymaker.get_gemini_model(model_key)
    if gemini is None:
        raise LLMUnavailableError("Gemini 모델을 초기화할 수 없습니다.")
    try:
        response = gemini.generate_content(prompt)
    except Exception as e:
        err = str(e)
        if not _is_quota_error(err):
            raise LLMError(f"Gemini 호출 실패: {e!s}", status_code=502) from e
        logger.warning("[gemini] 할당량 초과, %.1f초 후 1회 재시도", _RETRY_SLEEP_SECONDS)
        time.sleep(_RETRY_SLEEP_SECONDS)
        try:
            response = gemini.generate_content(prompt)
        except Exception as retry_error:
            raise LLMError(
                "Gemini 할당량이 초과되었습니다. 잠시 후 다시 시도하세요.",
                status_code=429,
            ) from retry_error
    try:
        text = (response.text or "").strip()
    except ValueError as e:
        raise LLMError(f"응답을 읽을 수 없습니다: {e!s}", status_code=400) from e
    if not text:
        raise LLMError("모델이 빈 응답을 반환했습니다.", status_code=502)
    return text
