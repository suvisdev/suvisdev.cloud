import { safeApiErrorMessage } from "@/lib/user-facing-error"

/** count = 사람, bots = 봇(User-Agent 판정), one_shot = 사람 중 60초 안에 떠난 접속(2026-09-29). */
type DailyVisitorCount = { date: string; count: number; bots: number; one_shot: number }

export type VisitorSummary = {
  now_active: number
  today: number
  today_bots: number
  today_one_shot: number
  last_7_days_total: number
  cumulative_total: number
  last_7_days_series: DailyVisitorCount[]
}

type ApiErrorBody = { detail?: string | unknown }

/** 익명 방문자 heartbeat — 무인증 공개 엔드포인트, 실패해도 사용자에게 노출하지 않는다. */
export async function pingVisitor(visitorId: string): Promise<void> {
  try {
    await fetch(`/api/backend/api/v1/analytics/visitors/ping`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visitor_id: visitorId }),
    })
  } catch {
    // 방문 집계 실패는 방문자 경험에 영향을 주면 안 된다 — 조용히 무시.
  }
}

export async function getVisitorSummary(): Promise<VisitorSummary> {
  const res = await fetch("/api/backend/api/v1/analytics/visitors/summary")
  const data = (await res.json()) as VisitorSummary & ApiErrorBody
  if (!res.ok) {
    throw new Error(
      safeApiErrorMessage(data.detail, "방문자 통계를 가져오지 못했습니다.", res.status)
    )
  }
  return data
}
