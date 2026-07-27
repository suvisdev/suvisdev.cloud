"""관리자 전용 — 멀티에이전트 관리 대시보드 API (mock).

require_admin 가드로 보호된다. 지금은 전부 mock 데이터이며, 각 에이전트(Argus/
Loom/Atlas/Prisma/Sentinel/Echo/Chronos)가 실제로 완성되는 대로 해당 항목만
실제 interactor 호출로 교체한다(image-classifier 포함 8개 중 현재 실제 구현은
image-classifier뿐이나, 대시보드 API 형태를 통일하기 위해 지금은 이것도 mock).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from shared.security.require_admin import AdminPrincipal, require_admin

admin_agents_router = APIRouter(prefix="/admin/agents", tags=["admin"])

_AGENTS: dict[str, dict] = {
    "image-classifier": {
        "name": "포스터 장르 분류기",
        "description": "ConvNeXt-Nano — 영화 포스터 이미지를 6개 장르로 분류",
        "model": "convnext_nano (timm) + fine-tuned head",
        "status": "on",
    },
    "argus": {
        "name": "Argus",
        "description": "물체 감지",
        "model": "RT-DETR / YOLOv8 (예정)",
        "status": "off",
    },
    "loom": {
        "name": "Loom",
        "description": "시맨틱 세그멘테이션",
        "model": "SegFormer-B0 (예정)",
        "status": "off",
    },
    "atlas": {
        "name": "Atlas",
        "description": "자세 추정",
        "model": "ViTPose / RTMPose (예정)",
        "status": "off",
    },
    "prisma": {
        "name": "Prisma",
        "description": "이미지 생성",
        "model": "Stable Diffusion 1.5 (예정)",
        "status": "off",
    },
    "sentinel": {
        "name": "Sentinel",
        "description": "이상 탐지",
        "model": "PatchCore / EfficientAD (예정)",
        "status": "off",
    },
    "echo": {
        "name": "Echo",
        "description": "감성 분석",
        "model": "Qwen / KLUE-RoBERTa + QLoRA (예정)",
        "status": "off",
    },
    "chronos": {
        "name": "Chronos",
        "description": "동영상 분류",
        "model": "VideoMAE / X3D (예정)",
        "status": "off",
    },
}


class AgentSummarySchema(BaseModel):
    id: str
    name: str
    description: str
    status: str


class AgentDetailSchema(AgentSummarySchema):
    model: str


class ToggleResponseSchema(BaseModel):
    id: str
    status: str


class InvokeResponseSchema(BaseModel):
    id: str
    result: str
    mock: bool


class LogEntrySchema(BaseModel):
    timestamp: str
    message: str


def _get_agent_or_404(agent_id: str) -> dict:
    agent = _AGENTS.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"에이전트를 찾을 수 없습니다: {agent_id}")
    return agent


@admin_agents_router.get("", response_model=list[AgentSummarySchema])
async def list_agents(_: AdminPrincipal = Depends(require_admin)) -> list[AgentSummarySchema]:
    return [
        AgentSummarySchema(id=agent_id, name=a["name"], description=a["description"], status=a["status"])
        for agent_id, a in _AGENTS.items()
    ]


@admin_agents_router.get("/{agent_id}", response_model=AgentDetailSchema)
async def get_agent(
    agent_id: str, _: AdminPrincipal = Depends(require_admin)
) -> AgentDetailSchema:
    a = _get_agent_or_404(agent_id)
    return AgentDetailSchema(id=agent_id, name=a["name"], description=a["description"], status=a["status"], model=a["model"])


@admin_agents_router.post("/{agent_id}/toggle", response_model=ToggleResponseSchema)
async def toggle_agent(
    agent_id: str, _: AdminPrincipal = Depends(require_admin)
) -> ToggleResponseSchema:
    a = _get_agent_or_404(agent_id)
    a["status"] = "off" if a["status"] == "on" else "on"
    return ToggleResponseSchema(id=agent_id, status=a["status"])


@admin_agents_router.post("/{agent_id}/invoke", response_model=InvokeResponseSchema)
async def invoke_agent(
    agent_id: str, _: AdminPrincipal = Depends(require_admin)
) -> InvokeResponseSchema:
    _get_agent_or_404(agent_id)
    return InvokeResponseSchema(id=agent_id, result="mock 응답입니다 — 실제 연동 전.", mock=True)


@admin_agents_router.get("/{agent_id}/logs", response_model=list[LogEntrySchema])
async def get_agent_logs(
    agent_id: str, _: AdminPrincipal = Depends(require_admin)
) -> list[LogEntrySchema]:
    _get_agent_or_404(agent_id)
    now = datetime.now(UTC).isoformat()
    return [LogEntrySchema(timestamp=now, message=f"[mock] {agent_id} 로그 — 실제 연동 전.")]


@admin_agents_router.get("/{agent_id}/model", response_model=dict)
async def get_agent_model(
    agent_id: str, _: AdminPrincipal = Depends(require_admin)
) -> dict:
    a = _get_agent_or_404(agent_id)
    return {"id": agent_id, "model": a["model"], "status": a["status"]}
