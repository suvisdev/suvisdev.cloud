from __future__ import annotations

from pydantic import BaseModel


class JudgeIntroduceSchema(BaseModel):
    id: int
    name: str
