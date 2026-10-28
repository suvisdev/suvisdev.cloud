"""관리자 전용 — 운영 제어 버튼(2단계). PC 의 ops-agent(k8s/ops-agent)에 정해진 동작만 전달한다.

  GET  /admin/ops                      노트북 상태(Arda 컨테이너·AI 모드·GPU·Ollama 모델). 에이전트에 못 닿으면 reachable=false
  POST /admin/ops/arda/{start|stop}    Arda 노트북 온프레미스 켜기·끄기
  POST /admin/ops/arda/ai-mode         {"mode": "gpu"|"cpu"} 거짓말 탐지(음성 인식·표정) GPU·CPU
  POST /admin/ops/ollama/{load|unload} {"model": "..."} 노트북 GPU 에 모델 올리기·내리기

- 브라우저는 에이전트를 직접 부르지 않는다. 관리자 JWT(require_admin)를 여기서 확인하고, 에이전트 토큰
  (OPS_AGENT_TOKEN)은 서버 안에만 있다.
- 주소(OPS_AGENT_URL)는 노트북 Tailscale IP 하나 — 노트북 파드든 집컴 파드든 같은 값으로 닿는다
  (2026-10-28 실측: 두 경로 모두 401 = 닿고 토큰 확인).
- 누가 무엇을 눌렀는지 로그에 남긴다(관리자 id·이름·동작·결과).
- 에이전트가 거절한 이유(409 동작 중, 404 없는 모델 등)는 상태 코드 그대로 돌려준다.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from shared.security.require_admin import AdminPrincipal, require_admin

logger = logging.getLogger(__name__)

admin_ops_router = APIRouter(prefix="/admin/ops", tags=["admin"])

_DEFAULT_URL = "http://100.118.78.100:8210"
_STATUS_TIMEOUT = 10.0
# Arda 켜기(up -d)·GPU 전환은 이미지 기동과 모델 로드로 1~3분 걸린다. 에이전트 쪽 상한(300s)보다 조금 길게
_ACTION_TIMEOUT = 330.0


class AiModeRequest(BaseModel):
    mode: Literal["gpu", "cpu"]


class ModelRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)


def _config() -> tuple[str, str]:
    url = (os.getenv("OPS_AGENT_URL", "").strip() or _DEFAULT_URL).rstrip("/")
    token = os.getenv("OPS_AGENT_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="OPS_AGENT_TOKEN 이 설정되지 않았습니다.")
    return url, token


async def _agent(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    url, token = _config()
    timeout = _STATUS_TIMEOUT if method == "GET" else _ACTION_TIMEOUT
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.request(
                method, url + path, json=body, headers={"X-Ops-Token": token}
            )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail="노트북 제어 에이전트에 닿지 않습니다(노트북이 꺼졌거나 에이전트가 멈춤).",
        ) from e
    try:
        payload = res.json()
    except ValueError:
        payload = {}
    if res.status_code >= 400:
        detail = payload.get("error") if isinstance(payload, dict) else None
        raise HTTPException(
            status_code=res.status_code, detail=detail or f"에이전트 오류 {res.status_code}"
        )
    return payload if isinstance(payload, dict) else {}


async def _act(
    admin: AdminPrincipal, path: str, body: dict[str, Any] | None = None
) -> dict[str, Any]:
    target = (body or {}).get("model") or (body or {}).get("mode") or ""
    try:
        result = await _agent("POST", path, body)
    except HTTPException as e:
        logger.warning(
            "[admin/ops] user=%s(%s) %s %s → 실패 %s %s",
            admin.user_id,
            admin.username,
            path,
            target,
            e.status_code,
            e.detail,
        )
        raise
    logger.info("[admin/ops] user=%s(%s) %s %s → ok", admin.user_id, admin.username, path, target)
    return result


@admin_ops_router.get("")
async def get_ops(_: AdminPrincipal = Depends(require_admin)) -> dict[str, Any]:
    try:
        status = await _agent("GET", "/status")
    except HTTPException as e:
        if e.status_code != 503:
            raise
        return {"reachable": False, "detail": e.detail}
    return {"reachable": True, **status}


# /arda/ai-mode 를 /arda/{action} 보다 먼저 둔다 — 뒤에 두면 {action} 이 "ai-mode" 를 먼저 잡아 422 가 난다
@admin_ops_router.post("/arda/ai-mode")
async def arda_ai_mode(
    body: AiModeRequest, admin: AdminPrincipal = Depends(require_admin)
) -> dict[str, Any]:
    return await _act(admin, "/arda/ai-mode", {"mode": body.mode})


@admin_ops_router.post("/arda/{action}")
async def arda_action(
    action: Literal["start", "stop"], admin: AdminPrincipal = Depends(require_admin)
) -> dict[str, Any]:
    return await _act(admin, f"/arda/{action}")


@admin_ops_router.post("/ollama/{action}")
async def ollama_action(
    action: Literal["load", "unload"],
    body: ModelRequest,
    admin: AdminPrincipal = Depends(require_admin),
) -> dict[str, Any]:
    return await _act(admin, f"/ollama/{action}", {"model": body.model})
