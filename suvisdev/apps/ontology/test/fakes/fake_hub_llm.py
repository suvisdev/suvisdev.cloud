"""테스트 전용 HubLlmPort — 미리 정해둔 응답을 그대로 돌려주거나 실패를 흉내낸다."""

from __future__ import annotations

from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError


class FakeHubLlm(HubLlmPort):
    def __init__(self, *, response: str = "", raise_error: bool = False) -> None:
        self._response = response
        self._raise_error = raise_error
        self.received_prompts: list[str] = []

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        self.received_prompts.append(prompt)
        if self._raise_error:
            raise HubRagError("fake llm 실패", status_code=503)
        return self._response
