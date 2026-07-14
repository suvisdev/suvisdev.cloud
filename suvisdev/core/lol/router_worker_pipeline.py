"""Router model(exaone3.5:7.8b) → Worker model(exaone3.5:2.4b) 순차 실행 파이프라인.

RTX 3050 8GB VRAM 제약상 두 모델을 동시에 상주시키지 않는다. Router 판단 이후
Worker를 호출하기 전 model_switch_guard로 Router가 실제 언로드됐는지 확인한다.
"""

from __future__ import annotations

import os

from core.lol.model_switch_guard import wait_until_model_unloaded
from core.lol.t1_mid_faker_orchestrator import FakerOrchestratorError, T1MidFakerOrchestrator

_OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_ROUTER_MODEL = "exaone3.5:7.8b"
_WORKER_MODEL = "exaone3.5:2.4b"


class RouterWorkerPipeline:
    """Router/Worker 각각 keep_alive=0 전용 인스턴스로 호출해 상주를 남기지 않는다."""

    def __init__(
        self,
        *,
        router_model: str = _ROUTER_MODEL,
        worker_model: str = _WORKER_MODEL,
        base_url: str = _OLLAMA_BASE,
        timeout: float = 120.0,
        unload_timeout: float = 10.0,
        unload_poll_interval: float = 0.3,
    ) -> None:
        self._router_model = router_model
        self._base_url = base_url.rstrip("/")
        self._unload_timeout = unload_timeout
        self._unload_poll_interval = unload_poll_interval
        self._router = T1MidFakerOrchestrator(
            model=router_model, base_url=base_url, timeout=timeout, keep_alive="0"
        )
        self._worker = T1MidFakerOrchestrator(
            model=worker_model, base_url=base_url, timeout=timeout, keep_alive="0"
        )

    def route_then_run(
        self,
        routing_prompt: str,
        worker_prompt: str,
        *,
        routing_system: str | None = None,
        worker_system: str | None = None,
    ) -> tuple[str, str]:
        """Router 응답을 먼저 받고, Router 언로드를 확인한 뒤 Worker를 호출한다."""
        routing_response = self._router.generate(routing_prompt, system=routing_system)

        if not wait_until_model_unloaded(
            self._base_url,
            self._router_model,
            timeout=self._unload_timeout,
            poll_interval=self._unload_poll_interval,
        ):
            raise FakerOrchestratorError(
                f"Router model({self._router_model})이 {self._unload_timeout}초 내 언로드되지 않았습니다.",
                status_code=503,
            )

        worker_response = self._worker.generate(worker_prompt, system=worker_system)
        return routing_response, worker_response
