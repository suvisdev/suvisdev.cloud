"""Mycroft(시맨틱 게이트웨이 3번째 분기 — 범용 Gemini 응답) DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MycroftAskCommand:
    question: str
    system: str | None = None


@dataclass(frozen=True)
class MycroftAnswerDto:
    text: str
