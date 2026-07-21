from __future__ import annotations

from ontology.app.dtos.image_generation_dto import GeneratedImage
from ontology.app.ports.input.image_generation_use_case import ImageGenerationUseCase
from ontology.app.ports.output.image_generation_port import ImageGenerationPort


class ImageGenerationInteractor(ImageGenerationUseCase):
    """image_generation_router → 입력 포트 → 출력 포트(SD 1.5 + LoRA) → 이미지 생성."""

    def __init__(self, generator_port: ImageGenerationPort) -> None:
        self._generator_port = generator_port

    def generate(self, prompt: str, style: str = "") -> GeneratedImage:
        return self._generator_port.generate(prompt, style)
