"use client"

import { useEffect, useState } from "react"
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Loader2 } from "lucide-react"
import { getStats, type StatsData, type StatsPeriod } from "@/lib/admin-stats-api"

const PERIOD_LABEL: Record<StatsPeriod, string> = { day: "일", week: "주", month: "월" }

// 팔레트 검증: dataviz 스킬 scripts/validate_palette.js — 8슬롯 고정 순서, CVD ΔE 24.2 (light, surface #ffffff) 전체 통과.
const CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]

const tooltipStyle = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: 8,
  fontSize: 12,
  boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
}
const axisTick = { fontSize: 10, fill: "#94a3b8" }

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="mb-4 text-sm font-bold text-slate-800">{title}</h2>
      {children}
    </section>
  )
}

export default function AdminStatsOverviewPage() {
  const [period, setPeriod] = useState<StatsPeriod>("week")
  const [data, setData] = useState<StatsData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setData(null)
    getStats(period)
      .then(setData)
      .catch((e: Error) => setError(e.message))
  }, [period])

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <div className="flex rounded-full border border-slate-200 p-0.5">
          {(Object.keys(PERIOD_LABEL) as StatsPeriod[]).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPeriod(p)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                period === p ? "bg-emerald-100 text-emerald-700" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {PERIOD_LABEL[p]}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
          {error}
        </p>
      )}

      {!data ? (
        <div className="flex items-center justify-center py-20 text-sm text-slate-400">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          불러오는 중...
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard title="에이전트 호출 수 추이">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={data.callTrend} margin={{ left: -20, right: 8 }}>
                <CartesianGrid vertical={false} stroke="#e2e8f0" strokeWidth={1} />
                <XAxis dataKey="label" tick={axisTick} axisLine={{ stroke: "#e2e8f0" }} tickLine={false} />
                <YAxis tick={axisTick} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line
                  type="monotone"
                  dataKey="value"
                  name="호출 수"
                  stroke="#2a78d6"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#2a78d6", stroke: "#fff", strokeWidth: 2 }}
                  activeDot={{ r: 5, fill: "#2a78d6", stroke: "#fff", strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="에이전트별 사용 비율">
            <div className="flex flex-col items-center gap-4 sm:flex-row">
              <ResponsiveContainer width="100%" height={200} className="sm:max-w-[200px]">
                <PieChart>
                  <Pie
                    data={data.agentUsage}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={2}
                    strokeWidth={2}
                    stroke="#fff"
                  >
                    {data.agentUsage.map((entry, i) => (
                      <Cell key={entry.name} fill={CATEGORICAL[i % CATEGORICAL.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <ul className="grid w-full grid-cols-2 gap-x-3 gap-y-1.5 sm:flex-1">
                {data.agentUsage.map((entry, i) => (
                  <li key={entry.name} className="flex items-center gap-1.5 text-xs">
                    <span
                      className="h-2 w-2 shrink-0 rounded-[2px]"
                      style={{ backgroundColor: CATEGORICAL[i % CATEGORICAL.length] }}
                    />
                    <span className="truncate text-slate-700">{entry.name}</span>
                    <span className="ml-auto shrink-0 text-slate-400">{entry.value}</span>
                  </li>
                ))}
              </ul>
            </div>
          </ChartCard>

          <ChartCard title="사용자 활동">
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={data.userActivity} margin={{ left: -20, right: 8 }}>
                <CartesianGrid vertical={false} stroke="#e2e8f0" strokeWidth={1} />
                <XAxis dataKey="label" tick={axisTick} axisLine={{ stroke: "#e2e8f0" }} tickLine={false} />
                <YAxis tick={axisTick} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Area
                  type="monotone"
                  dataKey="value"
                  name="활동 사용자"
                  stroke="#4a3aa7"
                  strokeWidth={2}
                  fill="#4a3aa7"
                  fillOpacity={0.1}
                />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      )}
    </div>
  )
}
