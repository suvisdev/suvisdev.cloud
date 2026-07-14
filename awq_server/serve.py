"""EXAONE-3.5-7.8B-Instruct-AWQ 직접 서빙 마이크로서비스.

suvisdev 메인 백엔드와 별개 프로세스로, 별도 venv(~/.venv-exaone)에서 기동한다.
Ollama가 exaone3.5:7.8b/2.4b를 서빙하는 것과 동일한 역할 — 다만 이쪽은 AWQ 체크포인트를
transformers+gptqmodel로 직접 로드해 RAG 생성 전용으로 쓴다 (core/lol/awq_exaone_orchestrator.py가
HTTP로 이 서버를 호출한다).

기동:
    source ~/.venv-exaone/bin/activate
    uvicorn awq_server.serve:app --host 0.0.0.0 --port 8100
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("awq_server")

_MODEL_PATH = os.getenv(
    "AWQ_MODEL_PATH",
    "/home/a/projects/suvis/EXAONE-3.5-7.8B-Instruct-AWQ",
)
_MAX_NEW_TOKENS = int(os.getenv("AWQ_MAX_NEW_TOKENS", "512"))
_END_OF_TURN = "[|endofturn|]"

_state: dict[str, Any] = {"model": None, "tokenizer": None}
_generate_lock = asyncio.Lock()


def _load_model() -> None:
    """1회 로드 — 최초 호출 시 Marlin fp16 커널 JIT 컴파일로 오래 걸릴 수 있다(정상, 캐시 후 빨라짐)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    logger.info("[awq_server] 모델 로드 시작: %s", _MODEL_PATH)
    tokenizer = AutoTokenizer.from_pretrained(_MODEL_PATH, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        _MODEL_PATH,
        trust_remote_code=True,
        device_map="cuda:0" if torch.cuda.is_available() else "cpu",
    )
    model.eval()
    _state["model"] = model
    _state["tokenizer"] = tokenizer
    logger.info("[awq_server] 모델 로드 완료")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await run_in_threadpool(_load_model)
    yield


app = FastAPI(lifespan=lifespan)


class GenerateRequest(BaseModel):
    prompt: str
    system: str | None = None
    max_new_tokens: int | None = None


class GenerateResponse(BaseModel):
    text: str


def _generate_sync(prompt: str, system: str | None, max_new_tokens: int) -> str:
    import torch

    model = _state["model"]
    tokenizer = _state["tokenizer"]

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    input_ids = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt"
    ).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )

    new_tokens = output_ids[0][input_ids.shape[-1] :]
    text = tokenizer.decode(new_tokens, skip_special_tokens=False)
    text = text.split(_END_OF_TURN)[0].strip()
    return text


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"model_loaded": _state["model"] is not None}


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest) -> GenerateResponse:
    if _state["model"] is None:
        raise HTTPException(status_code=503, detail="모델이 아직 로드되지 않았습니다.")
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt가 비어 있습니다.")

    max_new_tokens = req.max_new_tokens or _MAX_NEW_TOKENS
    async with _generate_lock:  # GPU 1장 순차 호출 — 동시 generate 충돌 방지
        text = await run_in_threadpool(_generate_sync, req.prompt, req.system, max_new_tokens)

    if not text:
        raise HTTPException(status_code=502, detail="모델이 빈 응답을 반환했습니다.")
    return GenerateResponse(text=text)
