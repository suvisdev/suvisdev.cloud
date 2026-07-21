from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.image_generation_dto import GeneratedImage


class ImageGenerationUseCase(ABC):
    """이미지 생성 입력 포트 (ABC) — Prisma."""

    @abstractmethod
    def generate(self, prompt: str, style: str = "") -> GeneratedImage:
        pass
