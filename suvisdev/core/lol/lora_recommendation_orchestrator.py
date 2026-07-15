"""mova 채팅용 LoRA 파인튜닝 모델(lora_server) 직접 서빙 클라이언트.

~/.venv-exaone(별도 venv)에서 상주 로드된 `lora_server`(호스트, Ollama·awq_server와
동일 패턴의 별도 프로세스)를 HTTP로 호출한다. 인터페이스는
awq_exaone_orchestrator.AwqExaoneOrchestrator와 동일하게 맞춘다.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

_LORA_SERVER_BASE = os.getenv("LORA_SERVER_URL", "http://localhost:8200")


class LoraOrchestratorError(Exception):
    def __init__(self, detail: str, *, status_code: int = 503) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class LoraRecommendationOrchestrator:
    """mova 채팅용 파인튜닝 어댑터(lora_server) 기반 공용 오케스트레이터."""

    def __init__(self, *, base_url: str = _LORA_SERVER_BASE, timeout: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def is_ready(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{self._base_url}/health")
                return r.status_code == 200
        except httpx.TransportError:
            return False

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        payload: dict[str, str] = {"prompt": prompt}
        if system:
            payload["system"] = system
        logger.info("[LoraRecommendationOrchestrator] generate prompt_chars=%d", len(prompt))

        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.post(f"{self._base_url}/generate", json=payload)
        except httpx.TimeoutException as e:
            raise LoraOrchestratorError("LoRA 서버 응답 타임아웃", status_code=504) from e
        except httpx.TransportError as e:
            raise LoraOrchestratorError(
                f"LoRA 서버에 연결할 수 없습니다: {e!s}", status_code=503
            ) from e

        if r.status_code != 200:
            raise LoraOrchestratorError(
                f"LoRA 서버 호출 실패 (HTTP {r.status_code}): {r.text[:200]}",
                status_code=502,
            )

        text = (r.json().get("text") or "").strip()
        if not text:
            raise LoraOrchestratorError("LoRA 모델이 빈 응답을 반환했습니다.", status_code=502)
        return text
