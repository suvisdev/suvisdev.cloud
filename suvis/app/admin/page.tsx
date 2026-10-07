"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Activity, Bot, Loader2, Radar, Server, Users } from "lucide-react"
import { AdminMenuButton } from "./_components/admin-menu-button"
import { listAgents, type AgentSummary } from "@/lib/admin-api"
import {
  getActiveUserCount,
  getRecentActivity,
  getServingServer,
  getTodayCrawlCount,
  type ActivityItem,
  type ServingServer,
} from "@/lib/admin-dashboard-api"

type DashboardState = {
  agents: AgentSummary[]
  crawlCount: number
  userCount: number
  activity: ActivityItem[]
}

export default function AdminHomePage() {
  const [data, setData] = useState<DashboardState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [server, setServer] = useState<ServingServer | null>(null)
  const [serverError, setServerError] = useState(false)

  useEffect(() => {
    Promise.all([listAgents(), getTodayCrawlCount(), getActiveUserCount(), getRecentActivity()])
      .then(([agents, crawlCount, userCount, activity]) =>
        setData({ agents, crawlCount, userCount, activity }),
      )
      .catch((e: Error) => setError(e.message))
    // 대시보드와 따로 — 서버 정보가 실패해도 나머지는 보이게
    getServingServer()
      .then(setServer)
      .catch(() => setServerError(true))
  }, [])

  return (
    <div className="min-h-screen">
      <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <AdminMenuButton />
          <div>
            <h1 className="text-base font-bold text-slate-800 md:text-lg">홈</h1>
            <p className="text-xs text-slate-400">SUVIS 운영 현황</p>
          </div>
        </div>
        <div
          className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600"
          title={server?.node ? `노드: ${server.node}` : undefined}
        >
          <Server className="h-3.5 w-3.5 text-slate-400" />
          <span>서빙 서버</span>
          <span className="font-semibold text-slate-800">
            {server ? server.machine : serverError ? "확인 실패" : "…"}
          </span>
        </div>
      </header>

      <div className="p-4 md:p-6 lg:p-8">
        {error && (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
            {error}
          </p>
        )}

        {server && (
          <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-3 text-sm font-bold text-slate-800">챗봇 LLM 경로</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {[...new Set(server.chatbots.map((r) => r.chatbot))].map((name) => (
                <div key={name} className="rounded-xl bg-slate-50 px-4 py-3">
                  <p className="mb-1.5 text-xs font-semibold text-slate-800">{name}</p>
                  <ul className="space-y-1">
                    {server.chatbots
                      .filter((r) => r.chatbot === name)
                      .map((r) => (
                        <li key={r.step} className="flex justify-between gap-3 text-xs">
                          <span className="shrink-0 text-slate-400">{r.step}</span>
                          <span className="text-right font-medium text-slate-700">{r.target}</span>
                        </li>
                      ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        )}

        {!data ? (
          <div className="flex items-center justify-center py-20 text-sm text-slate-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            불러오는 중...
          </div>
        ) : (
          <>
            {/* 요약 카드 */}
            <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
              <StatCard icon={Bot} label="전체 에이전트" value={`${data.agents.length}개`} />
              <StatCard
                icon={Activity}
                label="실행중 / 대기"
                value={`${data.agents.filter((a) => a.status === "on").length} / ${data.agents.filter((a) => a.status === "off").length}`}
              />
              <StatCard icon={Radar} label="오늘 크롤링" value={`${data.crawlCount}건`} />
              <StatCard icon={Users} label="활성 사용자" value={`${data.userCount}명`} />
            </div>

            <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
              {/* 최근 활동 피드 */}
              <section className="rounded-2xl border border-slate-200 bg-white p-5">
                <h2 className="mb-4 text-sm font-bold text-slate-800">최근 활동</h2>
                {data.activity.length === 0 ? (
                  <p className="text-xs text-slate-400">최근 활동이 없습니다.</p>
                ) : (
                  <ul className="space-y-3">
                    {data.activity.map((item) => (
                      <li key={item.id} className="flex items-start gap-2.5">
                        <span
                          className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                            item.kind === "agent" ? "bg-violet-500" : "bg-blue-500"
                          }`}
                        />
                        <div className="min-w-0">
                          <p className="truncate text-xs font-medium text-slate-700">{item.label}</p>
                          <p className="text-[10px] text-slate-400">{item.time}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              {/* 에이전트 상태 그리드 */}
              <section className="rounded-2xl border border-slate-200 bg-white p-5">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-sm font-bold text-slate-800">에이전트 상태</h2>
                  <Link href="/admin/agents" className="text-xs font-medium text-emerald-600 hover:text-emerald-800">
                    전체 보기
                  </Link>
                </div>
                <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
                  {data.agents.map((agent) => (
                    <Link
                      key={agent.id}
                      href={`/admin/agents/${agent.id}`}
                      className="rounded-xl bg-slate-50 px-3 py-2.5 transition-colors hover:bg-slate-100"
                    >
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-[9px] font-semibold ${
                          agent.status === "on"
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-slate-200 text-slate-500"
                        }`}
                      >
                        {agent.status === "on" ? "ON" : "OFF"}
                      </span>
                      <p className="mt-1 truncate text-xs font-semibold text-slate-800">{agent.name}</p>
                    </Link>
                  ))}
                </div>
              </section>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2 text-slate-400">
        <Icon className="h-4 w-4" />
        <span className="text-xs">{label}</span>
      </div>
      <p className="mt-2 text-2xl font-bold text-slate-800">{value}</p>
    </div>
  )
}
