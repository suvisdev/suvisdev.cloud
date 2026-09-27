"""공용 오케스트레이터 — Ollama 로컬 LLM(기본 exaone3.5:7.8b) 호출 + 구조화 이해.

2026-09-27 개명(구 t1_mid_faker_orchestrator / T1MidFakerOrchestrator → suvisdev_orchestrator / SuvisdevOrchestrator). 두 단계를 제공한다:
- generate(): 프롬프트 → 텍스트 (RAG 답변·요약·분류 등, 기존 그대로)
- understand_json(): 프롬프트 → JSON 모드 호출 → dict. 형식이 깨지면 한 번 더 "JSON만"으로
  재시도한다. 앱 오케스트레이터(mova ChatOrchestrator 등)의 "이해" 단계가 이걸 쓴다 —
  값의 검증(카탈로그·지도 대조)은 앱 몫이고 여기서는 형식만 보장한다.
"""

import json
import os
import re

import httpx

_OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_DEFAULT_MODEL = "exaone3.5:7.8b"
# 모델을 VRAM에 상주시켜 콜드 스타트 제거. -1 = 영구 상주.
_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")


class SuvisdevOrchestratorError(Exception):
    def __init__(self, detail: str, *, status_code: int = 503) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class SuvisdevOrchestrator:
    """Ollama 로컬 LLM 오케스트레이터. model 인자로 다른 모델(qwen3:4b 등)도 띄울 수 있다."""

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

    def _build_body(
        self,
        prompt: str,
        *,
        system: str | None,
        temperature: float | None,
        num_ctx: int | None,
        json_format: bool = False,
    ) -> dict[str, object]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body: dict[str, object] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "keep_alive": self._keep_alive,
        }
        if json_format:
            # ollama의 JSON 모드 — 구조화 출력(슬롯 추출 등)에서 산문이 섞이는 것을 막는다.
            body["format"] = "json"
        options: dict[str, float | int] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if num_ctx is not None:
            # ollama 기본 컨텍스트는 4096 — 긴 근거를 넣을 때 명시하지 않으면 앞부분이
            # 조용히 잘린다(2026-09-27 포트폴리오 채팅 실측: 근거 2,240토큰 + 시스템 프롬프트).
            options["num_ctx"] = num_ctx
        if options:
            body["options"] = options
        return body

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        num_ctx: int | None = None,
        json_format: bool = False,
    ) -> str:
        """프롬프트를 self._model에 전달하고 응답 문자열을 반환한다.

        temperature를 주지 않으면 모델 Modelfile 기본값을 쓴다(exaone3.5는 1).
        num_ctx를 주지 않으면 ollama 기본(4096)을 쓴다. json_format=True면 JSON만 받는다.
        """
        body = self._build_body(
            prompt, system=system, temperature=temperature, num_ctx=num_ctx, json_format=json_format
        )

        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.post(f"{self._base_url}/api/chat", json=body)
        except httpx.TimeoutException as e:
            raise SuvisdevOrchestratorError("Ollama 응답 타임아웃", status_code=504) from e
        except httpx.TransportError as e:
            raise SuvisdevOrchestratorError(
                f"Ollama 서버에 연결할 수 없습니다: {e!s}", status_code=503
            ) from e

        if r.status_code != 200:
            raise SuvisdevOrchestratorError(
                f"Ollama 호출 실패 (HTTP {r.status_code}): {r.text[:200]}",
                status_code=502,
            )

        data = r.json()
        text = (data.get("message", {}).get("content") or "").strip()
        if not text:
            raise SuvisdevOrchestratorError("모델이 빈 응답을 반환했습니다.", status_code=502)
        return text

    def understand_json(
        self,
        prompt: str,
        *,
        system: str | None = None,
        num_ctx: int | None = 2048,
        temperature: float = 0.0,
    ) -> dict[str, object]:
        """구조화 이해 — JSON 모드로 호출해 dict를 돌려준다.

        모델이 산문을 섞거나 깨진 JSON을 내면(JSON 모드에서도 드물게 발생) 본문에서 첫
        객체를 잘라 파싱하고, 그래도 안 되면 "JSON 객체 하나만 출력"을 덧붙여 1회 재시도.
        끝내 실패하면 SuvisdevOrchestratorError(502).
        """
        raw = self.generate(
            prompt, system=system, temperature=temperature, num_ctx=num_ctx, json_format=True
        )
        parsed = _parse_json_object(raw)
        if parsed is not None:
            return parsed
        retry = self.generate(
            f"{prompt}\n\n(JSON 객체 하나만 출력한다. 설명 금지.)",
            system=system,
            temperature=temperature,
            num_ctx=num_ctx,
            json_format=True,
        )
        parsed = _parse_json_object(retry)
        if parsed is None:
            raise SuvisdevOrchestratorError(f"JSON 이해 실패: {retry[:120]}", status_code=502)
        return parsed


def _parse_json_object(raw: str) -> dict[str, object] | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None
