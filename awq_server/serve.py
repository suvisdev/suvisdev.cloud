"""EXAONE-3.5-7.8B AWQ 체크포인트를 gptqmodel로 직접 서빙하는 RAG용 보조 서버.

Router/Worker(Ollama)와 완전히 별개 프로세스·venv(~/.venv-exaone)로 호스트에서 기동한다.
backend=BACKEND.TORCH 고정 — 이 WSL GPU 패스스루 환경에서 기본 선택 커널인 AwqMarlinLinear가
로드 시 응답 없이 멈추는 현상을 확인해 순수 torch 커널로 강제한다.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from gptqmodel import BACKEND, GPTQModel
from pydantic import BaseModel
from transformers import AutoTokenizer

_MODEL_PATH = os.getenv(
    "AWQ_MODEL_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "EXAONE-3.5-7.8B-Instruct-AWQ"),
)

_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["tokenizer"] = AutoTokenizer.from_pretrained(_MODEL_PATH, trust_remote_code=True)
    _state["model"] = GPTQModel.load(
        _MODEL_PATH, device="cuda:0", trust_remote_code=True, backend=BACKEND.TORCH
    )
    yield
    _state.clear()


app = FastAPI(lifespan=lifespan)


class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 256


class GenerateResponse(BaseModel):
    response: str


@app.get("/health")
def health() -> dict[str, bool]:
    return {"model_loaded": "model" in _state}


@app.post("/generate")
def generate(req: GenerateRequest) -> GenerateResponse:
    tokenizer = _state["tokenizer"]
    model = _state["model"]

    messages = [{"role": "user", "content": req.prompt}]
    inputs = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt"
    ).to("cuda:0")
    out = model.generate(inputs=inputs, max_new_tokens=req.max_new_tokens)
    completion = tokenizer.decode(
        out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
    )
    return GenerateResponse(response=completion)
