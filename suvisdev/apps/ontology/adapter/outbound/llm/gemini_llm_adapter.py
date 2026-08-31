"""Gemini API 직접 호출 어댑터 — HubLlmPort 구현체.

시맨틱 인텐트 게이트웨이의 3번째 분기(RAG도 CRUD도 아닌 범용 질의) 응답용.
mova의 gemini_client.gemini_reply와 원칙은 같지만(core.matrix 키메이커 재사용),
Hub(ontology)는 Spoke(mova)를 import할 수 없어 별도로 둔다.
"""

from __future__ import annotations

import asyncio

from core.matrix.vauly_keymaker_secret_manager import get_keymaker
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError


class GeminiLlmAdapter(HubLlmPort):
    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        return await asyncio.to_thread(self._generate_sync, prompt, system)

    def _generate_sync(self, prompt: str, system: str | None) -> str:
        keymaker = get_keymaker()
        if not keymaker.is_gemini_ready():
            raise HubRagError(
                "GEMINI_API_KEY가 설정되지 않았습니다. suvisdev/.env 에 키를 설정하세요.",
                status_code=503,
            )
        client = keymaker.genai_client
        if client is None:
            raise HubRagError("Gemini 모델을 초기화할 수 없습니다.", status_code=503)

        model_id = keymaker.resolve_model_id(None)
        content = f"{system}\n\n{prompt}" if system else prompt
        try:
            response = client.models.generate_content(model=model_id, contents=content)
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "resource_exhausted" in err.lower():
                raise HubRagError(
                    "Gemini 할당량이 초과되었습니다. 잠시 후 다시 시도하세요.", status_code=429
                ) from e
            raise HubRagError(f"Gemini 호출 실패: {e!s}", status_code=502) from e

        try:
            text = (response.text or "").strip()
        except ValueError as e:
            raise HubRagError(f"응답을 읽을 수 없습니다: {e!s}", status_code=400) from e
        if not text:
            raise HubRagError("Gemini 모델이 빈 응답을 반환했습니다.", status_code=502)
        return text
