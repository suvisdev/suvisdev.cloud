from __future__ import annotations

from dispatch.adapter.inbound.api.schemas.judge_schema import JudgeIntroduceSchema
from dispatch.app.dtos.judge_dto import JudgeIntroduceQuery, JudgeIntroduceResponse
from dispatch.app.ports.input.judge_use_case import JudgeUseCase
from dispatch.app.ports.output.judge_port import JudgePort


class JudgeInteractor(JudgeUseCase):
    def __init__(self, *, repository: JudgePort) -> None:
        self._repository = repository

    async def introduce_myself(self, schema: JudgeIntroduceSchema) -> JudgeIntroduceResponse:
        return await self._repository.introduce_myself(
            JudgeIntroduceQuery(id=schema.id, name=schema.name)
        )
