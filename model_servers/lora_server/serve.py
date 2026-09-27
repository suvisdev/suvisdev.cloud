"""mova 채팅용 LoRA 파인튜닝 모델 서빙 — RAG 답변 생성 전용.

train_mova_lora.py가 남긴 ~/lora_adapters/LATEST(경로/백엔드/베이스모델 3줄)를 읽어
베이스 모델 + 최신 LoRA 어댑터를 로드한다. Router/Worker(Ollama), AWQ 직접 서빙
(awq_server)과 완전히 별개 프로세스·venv(~/.venv-exaone)로 호스트에서 기동한다.

주기적 재학습(train_mova_lora.py) 후에는 POST /reload로 최신 어댑터를 다시 읽어
프로세스 재시작 없이 교체한다.

LATEST가 없으면(예: 새 머신에 어댑터 백업이 아직 없는 경우) LoRA 없이
LORA_FALLBACK_BASE_MODEL/LORA_FALLBACK_BACKEND의 베이스 모델만으로 기동한다.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import torch
from fastapi import Depends, FastAPI, Header, HTTPException
from peft import PeftModel
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

_LATEST_FILE = Path(
    os.getenv("LORA_ADAPTERS_ROOT", str(Path.home() / "lora_adapters"))
) / "LATEST"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FALLBACK_BASE_MODEL = os.getenv(
    "LORA_FALLBACK_BASE_MODEL", str(_REPO_ROOT / "EXAONE-3.5-2.4B-Instruct-AWQ")
)
_FALLBACK_BACKEND = os.getenv("LORA_FALLBACK_BACKEND", "awq_gptqmodel")

_state: dict[str, Any] = {}


def _read_latest() -> tuple[str | None, str, str]:
    """LATEST가 없으면 어댑터 없이(None) 폴백 베이스 모델로 뜨도록 한다."""
    if not _LATEST_FILE.exists():
        return None, _FALLBACK_BACKEND, _FALLBACK_BASE_MODEL
    lines = _LATEST_FILE.read_text(encoding="utf-8").strip().splitlines()
    adapter_dir, backend, base_model_path = lines[0], lines[1], lines[2]
    return adapter_dir, backend, base_model_path


def _load(adapter_dir: str | None, backend: str, base_model_path: str) -> None:
    tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True)

    if backend == "awq_gptqmodel":
        # gptqmodel은 transformers v5를 요구해 v4 환경(hf 백엔드)에서는 임포트
        # 자체가 실패하므로 이 분기 안에서만 지연 임포트한다.
        import gptqmodel.nn_modules.qlinear.gemm_awq as _gemm_awq
        from gptqmodel import BACKEND, GPTQModel

        # peft==0.19.1이 gptqmodel의 최신 클래스명을 못 따라가는 업스트림 버그 우회
        # (backend와 무관하게 peft의 LoRA 디스패처가 항상 AWQ 체커부터 먼저 시도함).
        _gemm_awq.AwqGEMMQuantLinear = _gemm_awq.AwqGEMMLinear

        base = GPTQModel.load(
            base_model_path, device="cuda:0", trust_remote_code=True, backend=BACKEND.EXLLAMA_V2
        ).model
    else:
        base = AutoModelForCausalLM.from_pretrained(
            base_model_path,
            torch_dtype=torch.float16,
            device_map="cuda:0",
            trust_remote_code=True,
            # eager 대비 실측 소폭 개선 + 긴 컨텍스트에서 안정적 (2026-09-02 벤치)
            attn_implementation="sdpa",
        )

    model = PeftModel.from_pretrained(base, adapter_dir) if adapter_dir else base
    if adapter_dir and backend != "awq_gptqmodel":
        # 서빙 표준: LoRA 가중치를 베이스에 병합해 per-token 어댑터 matmul 제거.
        # 실측(2026-09-02, RTX 3050): 17.8 → 26.1 tok/s (sdpa 포함).
        model = model.merge_and_unload()
    model.eval()

    _state["tokenizer"] = tokenizer
    _state["model"] = model
    _state["adapter_dir"] = adapter_dir
    _state["backend"] = backend
    _state["base_model_path"] = base_model_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    adapter_dir, backend, base_model_path = _read_latest()
    _load(adapter_dir, backend, base_model_path)
    yield
    _state.clear()


app = FastAPI(lifespan=lifespan)


def require_lora_token(x_lora_token: str | None = Header(default=None)) -> None:
    """LORA_SERVER_TOKEN이 비어있으면(로컬 개발) 인증을 생략한다. 원격(Cloudflare
    Tunnel 등)으로 노출할 때만 값을 채워 활성화한다 — orchestrator 쪽
    (core/lol/lora_server_client.py)도 같은 값을 X-LoRA-Token
    헤더로 보내야 한다."""
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
    return {
        "model_loaded": "model" in _state,
        "adapter_dir": _state.get("adapter_dir"),
        "backend": _state.get("backend"),
    }


@app.post("/reload", dependencies=[Depends(require_lora_token)])
def reload_adapter() -> dict[str, object]:
    """train_mova_lora.py 재학습 후 최신 어댑터로 교체한다(프로세스 재시작 불필요)."""
    del _state["model"]
    torch.cuda.empty_cache()
    adapter_dir, backend, base_model_path = _read_latest()
    _load(adapter_dir, backend, base_model_path)
    return {"reloaded": True, "adapter_dir": adapter_dir}


@app.post("/generate", dependencies=[Depends(require_lora_token)])
def generate(req: GenerateRequest) -> GenerateResponse:
    tokenizer = _state["tokenizer"]
    model = _state["model"]

    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.append({"role": "user", "content": req.prompt})
    inputs = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
    ).to("cuda:0")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=req.max_new_tokens)
    completion = tokenizer.decode(
        out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
    )
    return GenerateResponse(text=completion)
