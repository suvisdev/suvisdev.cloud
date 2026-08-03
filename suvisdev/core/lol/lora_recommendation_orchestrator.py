"""mova 채팅용 LoRA 파인튜닝 모델(lora_server) 직접 서빙 클라이언트.

~/.venv-exaone(별도 venv)에서 상주 로드된 `lora_server`(호스트, Ollama·awq_server와
동일 패턴의 별도 프로세스)를 HTTP로 호출한다. 인터페이스는
awq_exaone_orchestrator.AwqExaoneOrchestrator와 동일하게 맞춘다.

LORA_SERVER_URL을 원격(Cloudflare Tunnel 등) 주소로 바꾸면 그대로 원격 GPU
서버를 호출한다 — 코드 변경 없이 env만 바꾸면 된다. 원격 노출 시 LORA_SERVER_TOKEN을
설정하면 X-LoRA-Token 헤더 인증이 활성화된다(lora_server 쪽도 동일 값 필요).
"""

from __future__ import annotations

import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

_LORA_SERVER_BASE = os.getenv("LORA_SERVER_URL", "http://localhost:8200")
_LORA_SERVER_TOKEN = os.getenv("LORA_SERVER_TOKEN", "")

_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)
_RETRY_ATTEMPTS = 2  # 최초 시도 + 1회 재시도
_RETRY_BACKOFF_SECONDS = 0.5


class LoraOrchestratorError(Exception):
    def __init__(self, detail: str, *, status_code: int = 503) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class LoraRecommendationOrchestrator:
    """mova 채팅용 파인튜닝 어댑터(lora_server) 기반 공용 오케스트레이터."""

    def __init__(
        self,
        *,
        base_url: str = _LORA_SERVER_BASE,
        timeout: httpx.Timeout = _DEFAULT_TIMEOUT,
        token: str = _LORA_SERVER_TOKEN,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._token = token

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

        headers = {"X-LoRA-Token": self._token} if self._token else {}

        try:
            r = self._post_with_retry(headers, payload)
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

    def _post_with_retry(
        self, headers: dict[str, str], payload: dict[str, str]
    ) -> httpx.Response:
        """네트워크 레벨 실패(타임아웃·연결 끊김)만 1회 재시도한다. HTTP 응답이
        오긴 왔으나 상태코드가 4xx/5xx인 경우는 재시도 대상이 아니다(호출자가
        즉시 처리)."""
        last_error: Exception | None = None
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    return client.post(
                        f"{self._base_url}/generate", json=payload, headers=headers
                    )
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_error = e
                if attempt < _RETRY_ATTEMPTS - 1:
                    logger.warning(
                        "[LoraRecommendationOrchestrator] 네트워크 실패, %.1fs 후 재시도: %s",
                        _RETRY_BACKOFF_SECONDS,
                        e,
                    )
                    time.sleep(_RETRY_BACKOFF_SECONDS)
        assert last_error is not None
        raise last_error
