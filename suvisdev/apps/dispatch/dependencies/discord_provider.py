from __future__ import annotations

import os

from dispatch.adapter.outbound.http.discord_outbound import DiscordWebhookOutbound
from dispatch.app.ports.input.discord_use_case import DiscordUseCase
from dispatch.app.use_cases.send_discord_interactor import SendDiscordInteractor


def get_discord_use_case() -> DiscordUseCase:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL이 설정되지 않았습니다. suvisdev/.env를 확인하세요.")
    return SendDiscordInteractor(discord=DiscordWebhookOutbound(webhook_url=webhook_url))
