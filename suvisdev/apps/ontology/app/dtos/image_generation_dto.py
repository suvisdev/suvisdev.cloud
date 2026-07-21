from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedImage:
    """생성된 이미지 — base64 PNG + 사용된 프롬프트."""

    image_b64: str
    prompt: str
