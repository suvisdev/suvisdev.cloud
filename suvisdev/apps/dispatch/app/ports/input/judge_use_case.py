from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.adapter.inbound.api.schemas.judge_schema import JudgeIntroduceSchema
from dispatch.app.dtos.judge_dto import JudgeIntroduceResponse


class JudgeUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, schema: JudgeIntroduceSchema) -> JudgeIntroduceResponse: ...
