"""LR-ASPP MobileNetV3(torchvision, Pascal VOC) 어댑터 —
SemanticSegmentationPort 구현체.

사전학습 가중치는 최초 실행 시 torch hub가 자동으로 다운로드한다(인터넷
필요, 이후엔 `~/.cache/torch/hub/checkpoints/`에 캐시돼 재사용). 학습은
하지 않고 사전학습 모델 추론만 한다 — GPU 없는 환경(CPU-only)을 전제로
torchvision.models.segmentation 중 가장 가벼운 lraspp_mobilenet_v3_large
(약 3.2M 파라미터)를 쓴다. Pascal VOC 21개 클래스로 학습돼 도로/보도 클래스는
없다(labs/README.md §03 참고).

전처리(`weights.transforms()`)가 짧은 변을 520px로 리사이즈하므로, 반환되는
SegmentationResult의 width/height는 원본 이미지 크기가 아니라 이 리사이즈된
마스크의 실제 크기다.
"""

from __future__ import annotations

import io

import numpy as np
import torch
from PIL import Image
from torchvision.models.segmentation import (
    LRASPP_MobileNet_V3_Large_Weights,
    lraspp_mobilenet_v3_large,
)

from labs.semantic_segmentation.dto import DetectedClass, SegmentationResult


class LrasppSegmentationAdapter:
    def __init__(self) -> None:
        weights = LRASPP_MobileNet_V3_Large_Weights.DEFAULT
        self._model = lraspp_mobilenet_v3_large(weights=weights)
        self._model.eval()
        self._preprocess = weights.transforms()
        self._categories = weights.meta["categories"]

    def segment(self, image_bytes: bytes) -> SegmentationResult:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        tensor = torch.from_numpy(np.array(image)).permute(2, 0, 1)
        batch = self._preprocess(tensor).unsqueeze(0)

        with torch.no_grad():
            logits = self._model(batch)["out"]
        probs = logits.softmax(dim=1)[0]
        mask = probs.argmax(dim=0)
        height, width = mask.shape

        detected_classes = [
            DetectedClass(
                label=self._categories[class_id],
                class_id=class_id,
                pixel_count=int((mask == class_id).sum()),
                confidence=float(probs[class_id][mask == class_id].mean()),
            )
            for class_id in torch.unique(mask).tolist()
        ]

        return SegmentationResult(
            width=width,
            height=height,
            class_mask=mask.tolist(),
            detected_classes=detected_classes,
        )
