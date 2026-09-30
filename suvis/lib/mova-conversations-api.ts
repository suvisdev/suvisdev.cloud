import { safeApiErrorMessage } from "@/lib/user-facing-error"

export type ConversationSummary = {
  id: number
  title: string
  updated_at: string
  message_count: number
}

export type ConversationMessage = {
  id: number
  role: "user" | "assistant"
  content: string
  meta: Record<string, unknown>
  created_at: string
}

export type ConversationDetail = {
  id: number
  title: string
  created_at: string
  updated_at: string
  messages: ConversationMessage[]
}

type ApiErrorBody = { detail?: unknown }

async function conversationsFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/mova/conversations${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),

    },
  })
  let data: (T & ApiErrorBody) | ApiErrorBody
  try {
    data = (await res.json()) as T & ApiErrorBody
  } catch {
    data = { detail: `응답 파싱 실패 (${res.status})` }
  }
  if (!res.ok) {
    throw new Error(
      safeApiErrorMessage(data.detail, "요청을 처리하지 못했습니다.", res.status),
    )
  }
  return data as T
}

export function listConversations(): Promise<ConversationSummary[]> {
  return conversationsFetch<ConversationSummary[]>("")
}

export function getConversation(id: number): Promise<ConversationDetail> {
  return conversationsFetch<ConversationDetail>(`/${id}`)
}

export function deleteConversation(id: number): Promise<{ status: string }> {
  return conversationsFetch<{ status: string }>(`/${id}`, { method: "DELETE" })
}
