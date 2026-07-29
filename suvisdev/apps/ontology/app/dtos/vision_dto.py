from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisionIntroduceQuery:
    id: int
    name: str


@dataclass(frozen=True)
class VisionIntroduceResponse:
    id: int
    name: str


@dataclass(frozen=True)
class VisionImageCommand:
    filename: str
    content: bytes
    # Sentinel 업로드 게이트(H6) 소프트 플래그 — interactor가 게이트 판정 후 채워
    # repository로 넘긴다(지속화 대상).
    poster_confidence: float = 0.0
    sharpness_score: float = 0.0
    is_poster_warning: bool = False


@dataclass(frozen=True)
class VisionUploadResponse:
    filename: str
    size_bytes: int
    saved_path: str
    # Sentinel 업로드 게이트(H6) 메타데이터 — interactor가 raw 점수로 채운다.
    # 블러는 하드 게이트(미달 시 업로드 자체가 반려되므로 저장까지 오면 통과한 값),
    # is_poster_warning은 소프트 플래그(차단 안 함, 경고만).
    poster_confidence: float = 0.0
    sharpness_score: float = 0.0
    is_poster_warning: bool = False
    # DB 폴백 저장소일 때만 채워짐(vision_uploads.id) — 어드민 오버라이드가
    # 이 id로 대상 row를 찾는다. S3 백엔드는 DB row가 없어 None.
    upload_id: int | None = None


@dataclass(frozen=True)
class VisionPosterFlagOverrideDto:
    """어드민이 Sentinel 소프트 플래그(is_poster_warning)를 수동 재판정한 결과."""

    upload_id: int
    is_poster_warning: bool
    updated: bool
