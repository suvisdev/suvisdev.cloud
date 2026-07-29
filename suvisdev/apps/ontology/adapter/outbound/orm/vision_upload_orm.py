from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_neo_theone_base import Base


class VisionUploadOrm(Base):
    __tablename__ = "vision_uploads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # Sentinel 업로드 게이트(H6) 소프트 플래그 지속화 — 이전엔 응답 DTO에만 있어
    # 요청-응답 사이클 밖으로 나가면 사라졌다.
    poster_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sharpness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_poster_warning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
