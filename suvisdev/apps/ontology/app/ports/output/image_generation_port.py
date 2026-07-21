from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.image_generation_dto import GeneratedImage


class ImageGenerationPort(ABC):
    """이미지 생성 아웃바운드 포트 (ABC) — Prisma."""

    @abstractmethod
    def generate(self, prompt: str, style: str = "") -> GeneratedImage:
        """텍스트 프롬프트로 이미지를 생성해 base64 PNG로 반환한다."""
