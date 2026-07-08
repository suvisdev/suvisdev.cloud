from __future__ import annotations

from typing import Literal

from core.matrix.vauly_keymaker_secret_manager import get_keymaker
from mova.app.ports.output.llm_errors import LLMError, LLMUnavailableError


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
        if "429" in err or "quota" in err.lower() or "resource_exhausted" in err.lower():
            raise LLMError(
                "Gemini 할당량이 초과되었습니다. 잠시 후 다시 시도하세요.",
                status_code=429,
            ) from e
        raise LLMError(f"Gemini 호출 실패: {e!s}", status_code=502) from e
    try:
        text = (response.text or "").strip()
    except ValueError as e:
        raise LLMError(f"응답을 읽을 수 없습니다: {e!s}", status_code=400) from e
    if not text:
        raise LLMError("모델이 빈 응답을 반환했습니다.", status_code=502)
    return text
