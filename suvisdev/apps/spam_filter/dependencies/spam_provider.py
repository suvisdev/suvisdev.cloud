from __future__ import annotations

from core.lol.t1_mid_faker_orchestrator import get_faker_orchestrator
from spam_filter.app.ports.input.spam_use_case import SpamClassifyUseCase
from spam_filter.app.use_cases.spam_classify_interactor import SpamClassifyInteractor


def get_spam_classify_use_case() -> SpamClassifyUseCase:
    return SpamClassifyInteractor(orchestrator=get_faker_orchestrator())
