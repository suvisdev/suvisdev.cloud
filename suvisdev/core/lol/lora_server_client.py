"""mova 채팅용 LoRA 파인튜닝 모델(lora_server :8200) HTTP 클라이언트 — 서킷 브레이커·재시도 포함.
(2026-09-27 개명: 구 lora_recommendation_orchestrator/LoraRecommendationOrchestrator — 오케스트레이터가
아니라 추천 트랙의 LLM 호출 클라이언트다.)

~/.venv-exaone(별도 venv)에서 상주 로드된 `lora_server`(호스트에서 도는 별도
프로세스, Ollama와 동일 패턴)를 HTTP로 호출한다. (구 awq_server :8100 체인은
2026-09-11 데드 코드 정리로 삭제됨 — GGUF 롤백 대상은 :8200 serve.py다.)

LORA_SERVER_URL을 원격(Cloudflare Tunnel 등) 주소로 바꾸면 그대로 원격 GPU
서버를 호출한다 — 코드 변경 없이 env만 바꾸면 된다. 원격 노출 시 LORA_SERVER_TOKEN을
설정하면 X-LoRA-Token 헤더 인증이 활성화된다(lora_server 쪽도 동일 값 필요).
"""

from __future__ import annotations

import logging
import os
import threading
import time

import httpx

logger = logging.getLogger(__name__)

_LORA_SERVER_BASE = os.getenv("LORA_SERVER_URL", "http://localhost:8200")
_LORA_SERVER_TOKEN = os.getenv("LORA_SERVER_TOKEN", "")

_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)
_RETRY_ATTEMPTS = 2  # 최초 시도 + 1회 재시도
_RETRY_BACKOFF_SECONDS = 0.5

# 서킷 브레이커 — 인스턴스가 요청마다 새로 만들어지므로(DI) 상태는 모듈 레벨 공유.
# 연속 실패가 임계에 닿으면 쿨다운 동안 HTTP 호출 없이 즉시 실패시켜, 죽은
# lora 서버에 요청마다 타임아웃(최대 60초)을 기다리는 것을 막는다.
_CIRCUIT_FAILURE_THRESHOLD = 2
_CIRCUIT_COOLDOWN_SECONDS = 60.0
_circuit_lock = threading.Lock()
_circuit_failures = 0
_circuit_open_until = 0.0


def _circuit_is_open() -> bool:
    with _circuit_lock:
        return time.monotonic() < _circuit_open_until


def _circuit_record_failure() -> None:
    global _circuit_failures, _circuit_open_until
    with _circuit_lock:
        _circuit_failures += 1
        if _circuit_failures >= _CIRCUIT_FAILURE_THRESHOLD:
            _circuit_open_until = time.monotonic() + _CIRCUIT_COOLDOWN_SECONDS
            logger.warning(
                "[LoraServerClient] 서킷 오픈 — 연속 %d회 실패, %.0fs 동안 즉시 실패 처리",
                _circuit_failures,
                _CIRCUIT_COOLDOWN_SECONDS,
            )


def _circuit_record_success() -> None:
    global _circuit_failures, _circuit_open_until
    with _circuit_lock:
        _circuit_failures = 0
        _circuit_open_until = 0.0


class LoraServerError(Exception):
    def __init__(self, detail: str, *, status_code: int = 503) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class LoraServerClient:
    """lora_server 호출 클라이언트 — 실패 3회면 60초 서킷 오픈, 그동안 호출자는 Gemini 폴백."""

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

        if _circuit_is_open():
            raise LoraServerError(
                "LoRA 서버 서킷 오픈 상태(연속 실패 후 쿨다운) — 즉시 실패 처리",
                status_code=503,
            )

        logger.info("[LoraServerClient] generate prompt_chars=%d", len(prompt))

        headers = {"X-LoRA-Token": self._token} if self._token else {}

        try:
            r = self._post_with_retry(headers, payload)
        except httpx.TimeoutException as e:
            _circuit_record_failure()
            raise LoraServerError("LoRA 서버 응답 타임아웃", status_code=504) from e
        except httpx.TransportError as e:
            _circuit_record_failure()
            raise LoraServerError(f"LoRA 서버에 연결할 수 없습니다: {e!s}", status_code=503) from e

        if r.status_code != 200:
            _circuit_record_failure()
            raise LoraServerError(
                f"LoRA 서버 호출 실패 (HTTP {r.status_code}): {r.text[:200]}",
                status_code=502,
            )

        text = (r.json().get("text") or "").strip()
        if not text:
            _circuit_record_failure()
            raise LoraServerError("LoRA 모델이 빈 응답을 반환했습니다.", status_code=502)
        _circuit_record_success()
        return text

    def _post_with_retry(self, headers: dict[str, str], payload: dict[str, str]) -> httpx.Response:
        """네트워크 레벨 실패(타임아웃·연결 끊김)만 1회 재시도한다. HTTP 응답이
        오긴 왔으나 상태코드가 4xx/5xx인 경우는 재시도 대상이 아니다(호출자가
        즉시 처리)."""
        last_error: Exception | None = None
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    return client.post(f"{self._base_url}/generate", json=payload, headers=headers)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_error = e
                if attempt < _RETRY_ATTEMPTS - 1:
                    logger.warning(
                        "[LoraServerClient] 네트워크 실패, %.1fs 후 재시도: %s",
                        _RETRY_BACKOFF_SECONDS,
                        e,
                    )
                    time.sleep(_RETRY_BACKOFF_SECONDS)
        assert last_error is not None
        raise last_error
