"""T1 미드 페이커 — exaone3.5:7.8b (Ollama) 공용 오케스트레이터."""

from __future__ import annotations

import os

import httpx

_OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_DEFAULT_MODEL = "exaone3.5:7.8b"
# 모델을 VRAM에 상주시켜 콜드 스타트 제거. -1 = 영구 상주.
_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")


class FakerOrchestratorError(Exception):
    def __init__(self, detail: str, *, status_code: int = 503) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class T1MidFakerOrchestrator:
    """exaone3.5:7.8b (Ollama) 기반 공용 오케스트레이터. model 인자로 다른 버전도 띄울 수 있다."""

    def __init__(
        self,
        *,
        model: str = _DEFAULT_MODEL,
        base_url: str = _OLLAMA_BASE,
        timeout: float = 120.0,
        keep_alive: str = _KEEP_ALIVE,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._keep_alive = keep_alive

    def is_ready(self) -> bool:
        """Ollama 서버가 응답하는지 확인한다."""
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{self._base_url}/api/tags")
                return r.status_code == 200
        except httpx.TransportError:
            return False

    def warmup(self) -> bool:
        """모델을 미리 메모리에 올려 콜드 스타트를 제거한다. 실패해도 무시."""
        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": [],
                        "keep_alive": self._keep_alive,
                    },
                )
            return r.status_code == 200
        except httpx.TransportError:
            return False

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        """프롬프트를 self._model에 전달하고 응답 문자열을 반환한다."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": messages,
                        "stream": False,
                        "keep_alive": self._keep_alive,
                    },
                )
        except httpx.TimeoutException as e:
            raise FakerOrchestratorError("Ollama 응답 타임아웃", status_code=504) from e
        except httpx.TransportError as e:
            raise FakerOrchestratorError(
                f"Ollama 서버에 연결할 수 없습니다: {e!s}", status_code=503
            ) from e

        if r.status_code != 200:
            raise FakerOrchestratorError(
                f"Ollama 호출 실패 (HTTP {r.status_code}): {r.text[:200]}",
                status_code=502,
            )

        data = r.json()
        text = (data.get("message", {}).get("content") or "").strip()
        if not text:
            raise FakerOrchestratorError("모델이 빈 응답을 반환했습니다.", status_code=502)
        return text


_orchestrator = T1MidFakerOrchestrator()


def get_faker_orchestrator() -> T1MidFakerOrchestrator:
    return _orchestrator
