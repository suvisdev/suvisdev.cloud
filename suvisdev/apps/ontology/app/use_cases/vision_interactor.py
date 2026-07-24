from __future__ import annotations

import asyncio
from dataclasses import replace

from ontology.adapter.inbound.api.schemas.vision_schema import VisionIntroduceSchema
from ontology.app.dtos.vision_dto import (
    VisionImageCommand,
    VisionIntroduceQuery,
    VisionIntroduceResponse,
    VisionUploadResponse,
)
from ontology.app.ports.input.vision_use_case import VisionUseCase
from ontology.app.ports.output.anomaly_detection_port import AnomalyDetectionPort
from ontology.app.ports.output.vision_port import VisionPort

_ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png")

# 업로드 게이트 정책 임계값은 interactor가 소유한다(어댑터의 기본 판정과 분리 —
# 어댑터 부울 is_poster/is_blurry는 /sentinel/detect·MCP 직접 소비자용이고,
# 업로드 게이트는 raw 점수로 자체 정책을 적용해 역할별 분기 여지를 남긴다).
# 값 근거: 06_anomaly_detection_agent.md §6.5~§6.6.
_BLUR_THRESHOLD = 345.77  # Laplacian variance 하위 5퍼센타일(정상 포스터 232장)
_POSTER_CONFIDENCE_THRESHOLD = 0.5  # CLIP 제로샷 포스터 확률 결정 경계


class VisionInteractor(VisionUseCase):
    """vision_router → 입력 포트 → Sentinel 게이트 → 출력 포트(repository)."""

    def __init__(self, repository: VisionPort, anomaly_port: AnomalyDetectionPort) -> None:
        self._repository = repository
        self._anomaly_port = anomaly_port

    async def introduce_myself(
        self,
        schemas: VisionIntroduceSchema,
    ) -> VisionIntroduceResponse:
        return await self._repository.introduce_myself(
            VisionIntroduceQuery(id=schemas.id, name=schemas.name),
        )

    async def upload_image(
        self,
        filename: str,
        content: bytes,
    ) -> VisionUploadResponse:
        if not filename.lower().endswith(_ALLOWED_EXTENSIONS):
            raise ValueError("JPG 또는 PNG 이미지 파일만 업로드할 수 있습니다.")
        if not content:
            raise ValueError("빈 파일입니다.")

        # Sentinel 검수 — CLIP 로드가 있어 sync 추론을 스레드로 오프로드(이벤트 루프 보호)
        result = await asyncio.to_thread(self._anomaly_port.detect, content)

        # 블러: 하드 게이트 — 임계값 미달이면 반려(vision_router가 ValueError→400 매핑)
        if result.sharpness_score < _BLUR_THRESHOLD:
            raise ValueError(
                f"이미지가 너무 흐릿합니다(sharpness={result.sharpness_score:.1f} "
                f"< {_BLUR_THRESHOLD}). 더 선명한 이미지를 올려주세요."
            )

        # 포스터 여부: 소프트 — 차단하지 않고 경고 플래그만(제로샷 오탐 위험,
        # 티저·캐릭터 포스터가 오탐될 수 있어 어드민 오버라이드 여지를 남긴다).
        is_poster_warning = result.poster_confidence < _POSTER_CONFIDENCE_THRESHOLD

        response = await self._repository.save_image(
            VisionImageCommand(filename=filename, content=content),
        )
        return replace(
            response,
            poster_confidence=result.poster_confidence,
            sharpness_score=result.sharpness_score,
            is_poster_warning=is_poster_warning,
        )
