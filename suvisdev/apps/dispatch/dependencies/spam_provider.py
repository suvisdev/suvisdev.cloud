from __future__ import annotations

from core.lol.t1_mid_faker_orchestrator import T1MidFakerOrchestrator
from dispatch.app.ports.input.spam_use_case import SpamClassifyUseCase
from dispatch.app.use_cases.spam_classify_interactor import SpamClassifyInteractor

# 모든 spoke는 exaone3.5:2.4b 전용 인스턴스를 쓴다 (email_provider.py와 동일 패턴).
_SPAM_MODEL = "exaone3.5:2.4b"


def get_spam_classify_use_case() -> SpamClassifyUseCase:
    return SpamClassifyInteractor(orchestrator=T1MidFakerOrchestrator(model=_SPAM_MODEL))
