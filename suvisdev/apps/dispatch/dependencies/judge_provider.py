from __future__ import annotations

from fastapi import Depends

from dispatch.adapter.outbound.repositories.judge_repository import JudgeRepository
from dispatch.app.ports.input.judge_use_case import JudgeUseCase
from dispatch.app.ports.output.judge_port import JudgePort
from dispatch.app.use_cases.judge_interactor import JudgeInteractor


def get_judge_repository() -> JudgePort:
    return JudgeRepository()


def get_judge_use_case(
    repository: JudgePort = Depends(get_judge_repository),
) -> JudgeUseCase:
    return JudgeInteractor(repository=repository)
