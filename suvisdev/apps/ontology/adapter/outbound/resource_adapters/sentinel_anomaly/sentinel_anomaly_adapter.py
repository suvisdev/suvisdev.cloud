from __future__ import annotations

from io import BytesIO

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from ontology.app.dtos.anomaly_detection_dto import AnomalyResult
from ontology.app.ports.output.anomaly_detection_port import AnomalyDetectionPort

_CLIP_MODEL_ID = "openai/clip-vit-base-patch32"
_POSTER_PROMPTS = [
    "a movie poster",
    "an official theatrical movie poster with the film title",
]
_NON_POSTER_PROMPTS = [
    "a photograph",
    "a still frame from a movie scene or a portrait photo of a person",
]
# scripts/diagnose_sentinel_clip_poster_classifier.py — 제로샷 검증에서 쓴
# 결정 경계(AUROC 0.8844, 06_anomaly_detection_agent.md §6.6).
_POSTER_PROB_THRESHOLD = 0.5

# scripts/compute_sentinel_blur_threshold.py — 정상 포스터 232장
# (genre_classifier_train 전체)의 Laplacian variance(256x256 해상도
# 정규화 후) 하위 5퍼센타일. 06_anomaly_detection_agent.md §6.5~§6.6.
_BLUR_RESIZE = (256, 256)
_BLUR_THRESHOLD = 345.77


class SentinelAnomalyAdapter(AnomalyDetectionPort):
    """CLIP 제로샷(포스터 여부) + Laplacian variance(블러 여부) — Sentinel.

    두 체크 모두 06_anomaly_detection_agent.md §6.5~§6.6에서 검증됐다(포스터
    판별 AUROC 0.8844, 블러 분리 100%). CLIP은 echo_sentiment_adapter.py와
    동일하게 호출당 로드→추론→언로드(lora-server 상시 점유 고려, 00_COMMON
    §1.1). Laplacian은 opencv 경량 연산이라 로드/언로드가 필요 없다.
    """

    def __init__(self, *, device: str | None = None) -> None:
        self._device = device

    def detect(self, image: bytes) -> AnomalyResult:
        pil_image = Image.open(BytesIO(image)).convert("RGB")

        is_poster, poster_confidence = self._check_poster(pil_image)
        is_blurry, sharpness_score = self._check_blur(pil_image)

        return AnomalyResult(
            is_poster=is_poster,
            poster_confidence=poster_confidence,
            is_blurry=is_blurry,
            sharpness_score=sharpness_score,
        )

    def _check_poster(self, image: Image.Image) -> tuple[bool, float]:
        device = torch.device(self._device or ("cuda" if torch.cuda.is_available() else "cpu"))
        model = CLIPModel.from_pretrained(_CLIP_MODEL_ID)
        processor = CLIPProcessor.from_pretrained(_CLIP_MODEL_ID)
        try:
            model = model.to(device).eval()
        except RuntimeError:
            device = torch.device("cpu")
            model = model.to(device).eval()

        prompts = _POSTER_PROMPTS + _NON_POSTER_PROMPTS
        text_inputs = processor(text=prompts, return_tensors="pt", padding=True).to(device)
        image_inputs = processor(images=[image], return_tensors="pt").to(device)

        with torch.no_grad():
            text_features = model.get_text_features(**text_inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            image_features = model.get_image_features(**image_inputs)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            logits = 100.0 * image_features @ text_features.T
            sims = logits.softmax(dim=-1).cpu().numpy()[0]

        poster_confidence = float(sims[: len(_POSTER_PROMPTS)].sum())

        del model, processor, text_inputs, image_inputs, text_features, image_features, logits
        if device.type == "cuda":
            torch.cuda.empty_cache()

        return poster_confidence >= _POSTER_PROB_THRESHOLD, poster_confidence

    def _check_blur(self, image: Image.Image) -> tuple[bool, float]:
        gray = np.array(image.convert("L").resize(_BLUR_RESIZE, Image.BILINEAR))  # type: ignore[attr-defined]
        sharpness_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        return sharpness_score < _BLUR_THRESHOLD, sharpness_score
