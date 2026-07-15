"""EXAONE-3.5-7.8B-Instruct-AWQ 직접 서빙 클라이언트.

~/.venv-exaone(별도 venv, transformers+gptqmodel)에서 상주 로드된 `awq_server`(host, Ollama와
동일 패턴의 별도 프로세스)를 HTTP로 호출한다. suvisdev 메인 venv에는 무거운 AWQ 의존성을 넣지 않는다.
인터페이스는 t1_mid_faker_orchestrator.T1MidFakerOrchestrator와 동일하게 맞춘다.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

_AWQ_SERVER_BASE = os.getenv("AWQ_SERVER_URL", "http://localhost:8100")


class AwqOrchestratorError(Exception):
    def __init__(self, detail: str, *, status_code: int = 503) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class AwqExaoneOrchestrator:
    """EXAONE-3.5-7.8B-Instruct-AWQ(awq_server) 기반 공용 오케스트레이터."""

    def __init__(self, *, base_url: str = _AWQ_SERVER_BASE, timeout: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def is_ready(self) -> bool:
        """awq_server가 응답하는지 확인한다."""
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{self._base_url}/health")
                return r.status_code == 200
        except httpx.TransportError:
            return False

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        """프롬프트를 AWQ 모델에 전달하고 응답 문자열을 반환한다."""
        payload: dict[str, str] = {"prompt": prompt}
        if system:
            payload["system"] = system
        logger.info("[AwqExaoneOrchestrator] generate prompt_chars=%d", len(prompt))

        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.post(f"{self._base_url}/generate", json=payload)
        except httpx.TimeoutException as e:
            raise AwqOrchestratorError("AWQ 서버 응답 타임아웃", status_code=504) from e
        except httpx.TransportError as e:
            raise AwqOrchestratorError(
                f"AWQ 서버에 연결할 수 없습니다: {e!s}", status_code=503
            ) from e

        if r.status_code != 200:
            raise AwqOrchestratorError(
                f"AWQ 서버 호출 실패 (HTTP {r.status_code}): {r.text[:200]}",
                status_code=502,
            )

        text = (r.json().get("text") or "").strip()
        if not text:
            raise AwqOrchestratorError("AWQ 모델이 빈 응답을 반환했습니다.", status_code=502)
        return text
