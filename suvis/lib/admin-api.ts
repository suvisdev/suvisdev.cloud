import { safeApiErrorMessage } from "@/lib/user-facing-error"

export type AgentSummary = {
  id: string
  name: string
  description: string
  status: "on" | "off"
}

export type AgentDetail = AgentSummary & {
  model: string
}

export type AgentLogEntry = {
  timestamp: string
  message: string
}

type ApiErrorBody = { detail?: string | unknown }

async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/backend/viewer/admin/agents${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
    },
  })
  const data = (await res.json()) as T & ApiErrorBody
  if (!res.ok) {
    throw new Error(safeApiErrorMessage(data.detail, "요청을 처리하지 못했습니다.", res.status))
  }
  return data
}

export function listAgents(): Promise<AgentSummary[]> {
  return adminFetch<AgentSummary[]>("")
}

export function getAgent(id: string): Promise<AgentDetail> {
  return adminFetch<AgentDetail>(`/${id}`)
}

export function toggleAgent(id: string): Promise<{ id: string; status: "on" | "off" }> {
  return adminFetch(`/${id}/toggle`, { method: "POST" })
}

export function invokeAgent(id: string): Promise<{ id: string; result: string; mock: boolean }> {
  return adminFetch(`/${id}/invoke`, { method: "POST" })
}

export function getAgentLogs(id: string): Promise<AgentLogEntry[]> {
  return adminFetch<AgentLogEntry[]>(`/${id}/logs`)
}
