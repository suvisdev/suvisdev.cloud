from __future__ import annotations

import os

from core.lol.suvisdev_orchestrator import SuvisdevOrchestrator
from dispatch.adapter.outbound.http.n8n_gmail_outbound import N8nGmailOutbound
from dispatch.app.ports.input.email_use_case import EmailUseCase
from dispatch.app.use_cases.send_email_interactor import SendEmailInteractor
from ontology.app.use_cases.hub_email_orchestrator import HubEmailOrchestrator

# 오케스트레이터 기본 모델(exaone3.5:7.8b)과 별개로,
# 메일 본문 생성은 지금까지 검증된 exaone3.5:2.4b 전용 인스턴스를 그대로 쓴다.
_EMAIL_MODEL = "exaone3.5:2.4b"


def get_email_use_case() -> EmailUseCase:
    webhook_url = os.getenv("N8N_DISPATCH_WEBHOOK_URL", "")
    if not webhook_url:
        raise RuntimeError(
            "N8N_DISPATCH_WEBHOOK_URL이 설정되지 않았습니다. suvisdev/.env를 확인하세요."
        )
    return SendEmailInteractor(
        gmail=N8nGmailOutbound(webhook_url=webhook_url),
        hub=HubEmailOrchestrator(),
        orchestrator=SuvisdevOrchestrator(model=_EMAIL_MODEL),
    )
