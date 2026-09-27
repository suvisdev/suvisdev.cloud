import { authHeader } from "@/lib/suvis-session"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) || "http://127.0.0.1:8000"

type DailyVisitorCount = { date: string; count: number }

export type VisitorSummary = {
  now_active: number
  today: number
  last_7_days_total: number
  cumulative_total: number
  last_7_days_series: DailyVisitorCount[]
}

type ApiErrorBody = { detail?: string | unknown }

/** 익명 방문자 heartbeat — 무인증 공개 엔드포인트, 실패해도 사용자에게 노출하지 않는다. */
export async function pingVisitor(visitorId: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/v1/analytics/visitors/ping`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visitor_id: visitorId }),
    })
  } catch {
    // 방문 집계 실패는 방문자 경험에 영향을 주면 안 된다 — 조용히 무시.
  }
}

export async function getVisitorSummary(): Promise<VisitorSummary> {
  const res = await fetch("/api/analytics/visitors/summary", {
    headers: authHeader(),
  })
  const data = (await res.json()) as VisitorSummary & ApiErrorBody
  if (!res.ok) {
    throw new Error(
      safeApiErrorMessage(data.detail, "방문자 통계를 가져오지 못했습니다.", res.status)
    )
  }
  return data
}
