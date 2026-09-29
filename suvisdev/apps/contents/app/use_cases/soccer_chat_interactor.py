from __future__ import annotations

from contents.app.dtos.soccer_chat_dto import SoccerChatDto
from contents.app.ports.output.soccer_chat_errors import SoccerChatError
from core.lol.ollama_client import OllamaClient, OllamaClientError


def _build_prompt(messages: list[dict[str, str]]) -> str:
    """멀티턴 messages를 단일 프롬프트로 변환한다 (오케스트레이터는 단일 턴만 지원)."""
    turns = []
    for m in messages[:-1]:
        speaker = "사용자" if m.get("role") == "user" else "챗봇"
        turns.append(f"{speaker}: {m.get('content', '')}")
    last_user = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), ""
    )
    if not turns:
        return last_user
    history = "\n".join(turns)
    return f"이전 대화:\n{history}\n\n사용자: {last_user}"


class SoccerChatInteractor:
    def __init__(self, *, orchestrator: OllamaClient) -> None:
        self._orchestrator = orchestrator

    def chat(self, *, messages: list[dict[str, str]], system: str | None) -> SoccerChatDto:
        prompt = _build_prompt(messages)
        try:
            reply = self._orchestrator.generate(prompt, system=system)
        except OllamaClientError as e:
            raise SoccerChatError(e.detail, status_code=e.status_code) from e
        return SoccerChatDto(reply=reply)
