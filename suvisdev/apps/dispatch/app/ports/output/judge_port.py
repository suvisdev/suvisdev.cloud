from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.app.dtos.judge_dto import JudgeIntroduceQuery, JudgeIntroduceResponse


class JudgePort(ABC):
    @abstractmethod
    async def introduce_myself(self, query: JudgeIntroduceQuery) -> JudgeIntroduceResponse: ...
