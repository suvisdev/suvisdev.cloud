from __future__ import annotations

import io
import json
from pathlib import Path

import torch
from PIL import Image

from ontology.app.dtos.image_classifier_dto import Prediction
from ontology.app.ports.output.image_classifier_port import ImageClassifierPort

_MODEL_NAME = "convnext_nano"
_TOP_K = 3


class TimmConvnextAdapter(ImageClassifierPort):
    """ConvNeXt-Nano(timm) 파인튜닝 가중치로 포스터 장르를 분류한다.

    H1 VRAM 예산 판정(요청 시 로드 → 추론 → 언로드)에 따라 classify() 호출마다
    모델을 새로 올리고 끝나면 즉시 해제한다 — EXAONE/Ollama와 상시 VRAM 경합을
    피하기 위함이며, 평소엔 GPU 메모리를 전혀 점유하지 않는다.
    """

    def __init__(
        self, weights_path: Path, classes_path: Path, *, device: str | None = None
    ) -> None:
        self._weights_path = weights_path
        self._classes: dict[str, str] = json.loads(classes_path.read_text(encoding="utf-8"))
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    def classify(self, image: bytes) -> list[Prediction]:
        import timm
        from timm.data import create_transform, resolve_data_config

        model = timm.create_model(_MODEL_NAME, pretrained=False, num_classes=len(self._classes))
        model.load_state_dict(torch.load(self._weights_path, map_location="cpu"))
        model.eval().to(self._device)

        data_cfg = resolve_data_config({}, model=model)
        transform = create_transform(**data_cfg, is_training=False)

        pil_image = Image.open(io.BytesIO(image)).convert("RGB")
        inputs = transform(pil_image).unsqueeze(0).to(self._device)

        with torch.no_grad():
            logits = model(inputs)
            probs = torch.softmax(logits, dim=1)[0]

        top = torch.topk(probs, min(_TOP_K, len(self._classes)))
        predictions = [
            Prediction(label=self._classes[str(idx)], confidence=float(conf))
            for idx, conf in zip(top.indices.tolist(), top.values.tolist(), strict=True)
        ]

        del model, inputs
        if self._device == "cuda":
            torch.cuda.empty_cache()

        return predictions

    def supported_classes(self) -> list[str]:
        return list(self._classes.values())
