import { safeApiErrorMessage } from "@/lib/user-facing-error"

export type PortfolioChatTurn = { role: "user" | "assistant"; content: string }
export type PortfolioChatResponse = { reply: string; sources: string[] }

type ApiErrorBody = { detail?: unknown }

const FALLBACK_ERROR = "답변을 가져오지 못했어요. 잠시 후 다시 시도해 주세요."

async function portfolioFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/portfolio${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  })
  let data: unknown = null
  try {
    data = await res.json()
  } catch {
    data = null
  }
  if (!res.ok) {
    const detail =
      typeof data === "object" && data !== null ? (data as ApiErrorBody).detail : undefined
    throw new Error(safeApiErrorMessage(detail, FALLBACK_ERROR, res.status))
  }
  return data as T
}

export function sendPortfolioChat(
  message: string,
  history: PortfolioChatTurn[]
): Promise<PortfolioChatResponse> {
  return portfolioFetch<PortfolioChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ message, history: history.slice(-10) }),
  })
}
