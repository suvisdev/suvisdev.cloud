from __future__ import annotations

from pydantic import BaseModel


class WatcherIntroduceSchema(BaseModel):
    id: int
    name: str
