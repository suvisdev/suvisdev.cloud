from __future__ import annotations

from contents.app.ports.input.soccer_chat_use_case import SoccerChatUseCase
from contents.app.use_cases.soccer_chat_interactor import SoccerChatInteractor
from core.lol.suvisdev_orchestrator import SuvisdevOrchestrator

# 모든 spoke는 exaone3.5:2.4b 전용 인스턴스를 쓴다 (dispatch email_provider.py와 동일 패턴).
_SOCCER_CHAT_MODEL = "exaone3.5:2.4b"


def get_soccer_chat_use_case() -> SoccerChatUseCase:
    return SoccerChatInteractor(orchestrator=SuvisdevOrchestrator(model=_SOCCER_CHAT_MODEL))
