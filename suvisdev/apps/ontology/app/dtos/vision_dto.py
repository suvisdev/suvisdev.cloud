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


@dataclass(frozen=True)
class VisionUploadResponse:
    filename: str
    size_bytes: int
    saved_path: str
