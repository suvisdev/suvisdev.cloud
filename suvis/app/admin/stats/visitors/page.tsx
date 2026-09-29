"use client"

import { useEffect, useState } from "react"
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Loader2 } from "lucide-react"
import { getVisitorSummary, type VisitorSummary } from "@/lib/visitor-analytics-api"

const tooltipStyle = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: 8,
  fontSize: 12,
  boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
}
const axisTick = { fontSize: 10, fill: "#94a3b8" }

function StatTile({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold text-slate-800">
        {typeof value === "number" ? value.toLocaleString() : value}
      </p>
    </div>
  )
}

function formatDateLabel(iso: string): string {
  const [, month, day] = iso.split("-")
  return `${month}/${day}`
}

export default function AdminStatsVisitorsPage() {
  const [data, setData] = useState<VisitorSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getVisitorSummary()
      .then(setData)
      .catch((e: Error) => setError(e.message))
  }, [])

  if (error) {
    return (
      <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
        {error}
      </p>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-slate-400">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        불러오는 중...
      </div>
    )
  }

  const series = data.last_7_days_series.map((p) => ({
    label: formatDateLabel(p.date),
    value: p.count,
    bots: p.bots,
    oneShot: p.one_shot,
  }))

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatTile label="지금 접속" value={data.now_active} />
        <StatTile label="오늘 실방문" value={data.today} />
        <StatTile label="오늘 봇 / 1회성" value={`${data.today_bots} / ${data.today_one_shot}`} />
        <StatTile label="최근 7일" value={data.last_7_days_total} />
        <StatTile label="누적" value={data.cumulative_total} />
      </div>
      <p className="text-xs text-slate-500">
        실방문·최근 7일·누적은 봇(User-Agent 판정)을 뺀 값이에요. 1회성은 사람 중 60초 안에 떠난
        접속(첫 핑만 있음)이라 크롤러·미리보기·여러 브라우저 테스트가 섞여 있을 수 있어요.
      </p>

      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="mb-4 text-sm font-bold text-slate-800">최근 7일 방문자 추이</h2>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={series} margin={{ left: -20, right: 8 }}>
            <CartesianGrid vertical={false} stroke="#e2e8f0" strokeWidth={1} />
            <XAxis
              dataKey="label"
              tick={axisTick}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
            />
            <YAxis tick={axisTick} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line
              type="monotone"
              dataKey="value"
              name="실방문"
              stroke="#1baf7a"
              strokeWidth={2}
              dot={{ r: 3, fill: "#1baf7a", stroke: "#fff", strokeWidth: 2 }}
              activeDot={{ r: 5, fill: "#1baf7a", stroke: "#fff", strokeWidth: 2 }}
            />
            <Line
              type="monotone"
              dataKey="bots"
              name="봇"
              stroke="#94a3b8"
              strokeWidth={2}
              strokeDasharray="4 3"
              dot={{ r: 2, fill: "#94a3b8", stroke: "#fff", strokeWidth: 1 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </section>
    </div>
  )
}
