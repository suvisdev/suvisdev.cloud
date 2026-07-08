"""Spoke → Hub 이벤트 타입 정의."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DispatchEmailEvent:
    to: str
    prompt: str
    subject: str | None


@dataclass(frozen=True)
class InboundMessageEvent:
    """외부 채널(telegram·discord·email)로 인입된 메시지 이벤트."""

    channel: str
    sender: str
    body: str
    important_client: bool = False
