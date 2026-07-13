from __future__ import annotations

from pydantic import BaseModel, Field


class VisionIntroduceSchema(BaseModel):
    id: int = Field(0, description="Vision ID")
    name: str = Field("비전", description="Vision name")
