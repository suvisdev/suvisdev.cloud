"use client"

import { useEffect, useState } from "react"
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
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

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold text-slate-800">{value.toLocaleString()}</p>
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
      <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">{error}</p>
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

  const series = data.last_7_days_series.map((p) => ({ label: formatDateLabel(p.date), value: p.count }))

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="지금 접속" value={data.now_active} />
        <StatTile label="오늘" value={data.today} />
        <StatTile label="최근 7일" value={data.last_7_days_total} />
        <StatTile label="누적" value={data.cumulative_total} />
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="mb-4 text-sm font-bold text-slate-800">최근 7일 방문자 추이</h2>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={series} margin={{ left: -20, right: 8 }}>
            <CartesianGrid vertical={false} stroke="#e2e8f0" strokeWidth={1} />
            <XAxis dataKey="label" tick={axisTick} axisLine={{ stroke: "#e2e8f0" }} tickLine={false} />
            <YAxis tick={axisTick} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line
              type="monotone"
              dataKey="value"
              name="방문자"
              stroke="#1baf7a"
              strokeWidth={2}
              dot={{ r: 3, fill: "#1baf7a", stroke: "#fff", strokeWidth: 2 }}
              activeDot={{ r: 5, fill: "#1baf7a", stroke: "#fff", strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </section>
    </div>
  )
}
