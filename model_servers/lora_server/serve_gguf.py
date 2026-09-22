"""GGUF(llama.cpp) 서빙 파사드 — serve.py와 동일한 /health·/generate·/reload 계약.

fp16 transformers 서빙(serve.py)의 속도 한계(≈26tok/s)를 llama.cpp Q5_K_M로
대체한다(2026-09-02 전환). llama-server를 자식 프로세스(127.0.0.1:8201)로 띄우고
/generate를 OpenAI /v1/chat/completions로 변환 프록시한다. EC2 orchestrator
(core/lol/lora_recommendation_orchestrator.py)의 계약 — X-LoRA-Token 헤더,
{"prompt","system","max_new_tokens"} → {"text"} — 은 불변이라 백엔드 변경이 없다.

모델은 export_mova_gguf.py가 갱신하는 ~/lora_adapters/LATEST_GGUF(경로 1줄)를
읽는다. 재학습 후엔 export 실행 → POST /reload(자식 재기동)로 교체한다.
"""

from __future__ import annotations

import os
import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

_LATEST_GGUF = Path(
    os.getenv("LORA_ADAPTERS_ROOT", str(Path.home() / "lora_adapters"))
) / "LATEST_GGUF"
_LLAMA_SERVER_BIN = os.getenv(
    "LLAMA_SERVER_BIN", str(Path.home() / "llama.cpp/build/bin/llama-server")
)
_LLAMA_PORT = int(os.getenv("LORA_GGUF_PORT", "8201"))
_LLAMA_URL = f"http://127.0.0.1:{_LLAMA_PORT}"
_CTX_SIZE = os.getenv("LORA_GGUF_CTX", "4096")
# llama-server의 호스트 프롬프트 캐시 상한(MiB). 기본값 8192를 그대로 두면
# 상주 RSS가 5GB대까지 자라, 재학습 A/B로 테스트 서버를 하나 더 띄울 때
# RAM이 고갈된다(2026-09-17 실측: 운영 5.4GB + 테스트 6.1GB로 스크립트가
# killed). 채팅 프롬프트는 카탈로그가 매 질의 달라 공통 프리픽스가
# 시스템 프롬프트 정도뿐이라 1GB로 충분하다. 0은 비활성, -1은 무제한.
_CACHE_RAM_MIB = os.getenv("LORA_GGUF_CACHE_RAM", "1024")

_state: dict[str, Any] = {}


def _spawn() -> None:
    gguf_path = _LATEST_GGUF.read_text(encoding="utf-8").strip()
    proc = subprocess.Popen(
        [
            _LLAMA_SERVER_BIN,
            "-m", gguf_path,
            "--host", "127.0.0.1",
            "--port", str(_LLAMA_PORT),
            "-ngl", "99",
            "-c", _CTX_SIZE,
            "--cache-ram", _CACHE_RAM_MIB,
            "--jinja",
        ]
    )
    # llama-server는 로드 완료 전 /health가 503이다. 로드는 수 초면 끝난다.
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server 조기 종료 (exit={proc.returncode})")
        try:
            if httpx.get(f"{_LLAMA_URL}/health", timeout=2.0).status_code == 200:
                _state["proc"] = proc
                _state["gguf_path"] = gguf_path
                return
        except httpx.HTTPError:
            pass
        time.sleep(1.0)
    proc.terminate()
    raise RuntimeError("llama-server 로드 타임아웃(120s)")


def _terminate() -> None:
    proc = _state.pop("proc", None)
    if proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
    _state.pop("gguf_path", None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _spawn()
    yield
    _terminate()


app = FastAPI(lifespan=lifespan)


def require_lora_token(x_lora_token: str | None = Header(default=None)) -> None:
    """serve.py와 동일 — LORA_SERVER_TOKEN이 비어있으면(로컬 개발) 인증 생략."""
    expected = os.getenv("LORA_SERVER_TOKEN", "")
    if not expected:
        return
    if x_lora_token != expected:
        raise HTTPException(status_code=401, detail="invalid or missing token")


class GenerateRequest(BaseModel):
    prompt: str
    system: str | None = None
    max_new_tokens: int = 256


class GenerateResponse(BaseModel):
    text: str


@app.get("/health")
def health() -> dict[str, object]:
    proc = _state.get("proc")
    return {
        "model_loaded": proc is not None and proc.poll() is None,
        "adapter_dir": _state.get("gguf_path"),
        "backend": "gguf",
    }


@app.post("/reload", dependencies=[Depends(require_lora_token)])
def reload_adapter() -> dict[str, object]:
    """export_mova_gguf.py 실행 후 최신 GGUF로 자식 프로세스를 재기동한다."""
    _terminate()
    _spawn()
    return {"reloaded": True, "adapter_dir": _state.get("gguf_path")}


@app.post("/generate", dependencies=[Depends(require_lora_token)])
def generate(req: GenerateRequest) -> GenerateResponse:
    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.append({"role": "user", "content": req.prompt})
    try:
        r = httpx.post(
            f"{_LLAMA_URL}/v1/chat/completions",
            json={
                "messages": messages,
                "max_tokens": req.max_new_tokens,
                # serve.py의 HF generate 기본값(greedy)과 동일하게 결정론 생성
                "temperature": 0,
            },
            timeout=120.0,
        )
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"llama-server 오류: {e}") from e
    return GenerateResponse(text=r.json()["choices"][0]["message"]["content"])
