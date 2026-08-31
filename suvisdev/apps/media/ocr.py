"""S3 사진 OCR — Gemini 멀티모달. mova의 gemini_client.gemini_reply와 동일한
Keymaker 재사용·에러 매핑 원칙이나, 이미지 입력이라 별도로 둔다."""

from __future__ import annotations

from google.genai import types

from core.matrix.vauly_keymaker_secret_manager import get_keymaker

_OCR_PROMPT = "이 이미지에 보이는 텍스트를 그대로 추출해줘. 텍스트가 없으면 빈 문자열만 반환해."


def extract_text(image_bytes: bytes, content_type: str) -> str:
    keymaker = get_keymaker()
    if not keymaker.is_gemini_ready():
        raise RuntimeError(
            "GEMINI_API_KEY가 설정되지 않았습니다. suvisdev/.env 에 키를 설정하세요."
        )
    client = keymaker.genai_client
    if client is None:
        raise RuntimeError("Gemini 모델을 초기화할 수 없습니다.")

    model_id = keymaker.resolve_model_id(None)
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=content_type)
    try:
        response = client.models.generate_content(
            model=model_id, contents=[image_part, _OCR_PROMPT]
        )
    except Exception as e:
        raise RuntimeError(f"Gemini OCR 호출 실패: {e!s}") from e

    try:
        return (response.text or "").strip()
    except ValueError:
        return ""
