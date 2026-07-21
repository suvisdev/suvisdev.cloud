import { listAgents } from "@/lib/admin-api"

export type AgentSummaryStats = {
  total: number
  on: number
  off: number
}

export type ActivityItem = {
  id: string
  label: string
  time: string
  kind: "agent" | "crawl"
}

/** 실제 연동 — /viewer/admin/agents 목록에서 집계한다. */
export async function getAgentSummaryStats(): Promise<AgentSummaryStats> {
  const agents = await listAgents()
  const on = agents.filter((a) => a.status === "on").length
  return { total: agents.length, on, off: agents.length - on }
}

/** TODO: harvester 실행 이력 API 연동 전까지 mock. */
export async function getTodayCrawlCount(): Promise<number> {
  return 12
}

/** TODO: viewer users 카운트 API 연동 전까지 mock. */
export async function getActiveUserCount(): Promise<number> {
  return 4
}

/** TODO: 에이전트 invoke 로그 + harvester 실행 로그를 합쳐서 보여줄 API 연동 전까지 mock. */
export async function getRecentActivity(): Promise<ActivityItem[]> {
  return [
    { id: "1", label: "포스터 장르 분류기 테스트 호출", time: "10분 전", kind: "agent" },
    { id: "2", label: "KOBIS 일간 박스오피스 수집 완료", time: "1시간 전", kind: "crawl" },
    { id: "3", label: "TMDB top_rated 20편 반영", time: "3시간 전", kind: "crawl" },
    { id: "4", label: "포스터 장르 분류기 ON 전환", time: "어제", kind: "agent" },
  ]
}
