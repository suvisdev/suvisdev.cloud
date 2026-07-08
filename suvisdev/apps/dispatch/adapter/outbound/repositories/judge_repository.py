from __future__ import annotations

from dispatch.app.dtos.judge_dto import JudgeIntroduceQuery, JudgeIntroduceResponse
from dispatch.app.ports.output.judge_port import JudgePort


class JudgeRepository(JudgePort):
    async def introduce_myself(self, query: JudgeIntroduceQuery) -> JudgeIntroduceResponse:
        return JudgeIntroduceResponse(id=query.id, name=query.name)
