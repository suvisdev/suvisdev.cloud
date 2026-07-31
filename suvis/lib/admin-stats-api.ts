import { listAgents } from "@/lib/admin-api"

export type StatsPeriod = "day" | "week" | "month"

export type TrendPoint = { label: string; value: number }
export type AgentUsageSlice = { name: string; value: number }

export type StatsData = {
  callTrend: TrendPoint[]
  agentUsage: AgentUsageSlice[]
  userActivity: TrendPoint[]
}

const PERIOD_POINTS: Record<StatsPeriod, { count: number; labelOf: (i: number) => string }> = {
  day: { count: 24, labelOf: (i) => `${i}시` },
  week: { count: 7, labelOf: (i) => ["일", "월", "화", "수", "목", "금", "토"][i] },
  month: { count: 4, labelOf: (i) => `${i + 1}주차` },
}

/** 결정적 의사난수 — mock 시리즈가 기간 전환 시마다 흔들리지 않게 시드 고정. */
function seededSeries(seed: number, count: number, base: number, spread: number): number[] {
  let x = seed || 1
  const next = () => {
    x = (x * 1103515245 + 12345) & 0x7fffffff
    return x / 0x7fffffff
  }
  return Array.from({ length: count }, () => Math.round(base + next() * spread))
}

function buildTrend(period: StatsPeriod, seed: number, base: number, spread: number): TrendPoint[] {
  const { count, labelOf } = PERIOD_POINTS[period]
  return seededSeries(seed, count, base, spread).map((value, i) => ({ label: labelOf(i), value }))
}

/** TODO: 실제 통계 API 연동 전까지 mock. 에이전트별 사용 비율만 /viewer/admin/agents 실제 목록 기반. */
export async function getStats(period: StatsPeriod): Promise<StatsData> {
  const agents = await listAgents().catch(() => [])
  const usage = seededSeries(7, Math.max(agents.length, 1), 4, 40)
  const agentUsage: AgentUsageSlice[] = agents.length
    ? agents.map((a, i) => ({ name: a.name, value: usage[i] }))
    : [{ name: "데이터 없음", value: 1 }]

  return {
    callTrend: buildTrend(period, 1, 20, 60),
    agentUsage,
    userActivity: buildTrend(period, 3, 2, 10),
  }
}
