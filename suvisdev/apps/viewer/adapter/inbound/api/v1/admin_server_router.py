"""관리자 전용 — 지금 이 요청을 받은 서버와 챗봇별 LLM 경로 확인.

2026-11-08부터 노트북 한 대만 서빙한다(예전엔 노트북·집컴이 같은 앱을 띄우고 터널이 켜진 쪽으로 보냈다).
이 요청을 처리한 backend 파드의 노드 이름을 k8s downward API(`NODE_NAME`, k8s/backend.yaml)로 받아 돌려준다.

챗봇 LLM 경로:
- `PORTFOLIO_LLM_OLLAMA_URL` 은 노트북 GPU 올라마(:11434)를 가리킨다.
- `OLLAMA_BASE_URL`(:11435 HAProxy)은 노트북 올라마로 간다.
- lora-server 는 노트북 :8200 유저 서비스다.
"""

from __future__ import annotations

import asyncio
import os

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from shared.security.require_admin import AdminPrincipal, require_admin

admin_server_router = APIRouter(prefix="/admin/server", tags=["admin"])

_MACHINES = {
    "teagy": "노트북",
    "desktop-t89e5id": "집컴",
}


class ChatbotRouteSchema(BaseModel):
    chatbot: str
    step: str
    target: str


class ServerInfoSchema(BaseModel):
    node: str
    machine: str
    chatbots: list[ChatbotRouteSchema]


async def _up(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            return (await client.get(url)).status_code == 200
    except httpx.HTTPError:
        return False


async def _chatbot_routes() -> list[ChatbotRouteSchema]:
    laptop_ollama = (
        os.getenv("PORTFOLIO_LLM_OLLAMA_URL", "").strip()
        or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ).rstrip("/")
    lora = os.getenv("LORA_SERVER_URL", "http://localhost:8200").rstrip("/")
    laptop_gpu, lora_up = await asyncio.gather(
        _up(f"{laptop_ollama}/api/version"), _up(f"{lora}/health")
    )

    # 도메인 챗봇 — portfolio_chat_provider.get_portfolio_llm_port 와 같은 판정
    if os.getenv("PORTFOLIO_LLM_BACKEND", "exaone").strip().lower() == "gemini":
        portfolio = "Gemini"
    elif laptop_gpu:
        portfolio = f"노트북 GPU · {os.getenv('PORTFOLIO_LLM_MODEL', 'exaone3.5:7.8b')}"
    else:
        portfolio = "Gemini (노트북 GPU 없음 → 폴백)"

    # mova 질문 이해 — market_chat_provider.get_chat_agent / get_chat_orchestrator
    if os.getenv("MOVA_CHAT_AGENT", "0") in ("1", "true", "yes"):
        model = os.getenv("MOVA_AGENT_MODEL", "mova-agent-v9")
    elif os.getenv("MOVA_ORCHESTRATOR_ENABLED", "1") in ("0", "false", "no"):
        model = ""
    else:
        model = os.getenv("MOVA_ORCHESTRATOR_MODEL", "exaone3.5:7.8b")
    if not model:
        understand = "꺼짐 (규칙 기반)"
    elif laptop_gpu:
        understand = f"노트북 GPU · {model}"
    else:
        understand = f"집컴 CPU · {model} (예비)"

    # mova 추천 — market_chat_provider.get_recommendation_port
    if os.getenv("RECOMMENDATION_BACKEND", "lora") == "gemini":
        recommend = "Gemini"
    elif lora_up:
        recommend = "집컴 GPU · lora-server"
    else:
        recommend = "Gemini (lora-server 없음 → 폴백)"

    return [
        ChatbotRouteSchema(chatbot="도메인 챗봇", step="답변", target=portfolio),
        ChatbotRouteSchema(chatbot="mova 챗봇", step="질문 이해", target=understand),
        ChatbotRouteSchema(chatbot="mova 챗봇", step="추천", target=recommend),
    ]


@admin_server_router.get("", response_model=ServerInfoSchema)
async def get_server(_: AdminPrincipal = Depends(require_admin)) -> ServerInfoSchema:
    node = os.environ.get("NODE_NAME", "")
    return ServerInfoSchema(
        node=node,
        machine=_MACHINES.get(node, "알 수 없음"),
        chatbots=await _chatbot_routes(),
    )
