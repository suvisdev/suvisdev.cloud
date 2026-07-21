"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { ChevronRight, Loader2 } from "lucide-react"
import { AdminMenuButton } from "../_components/admin-menu-button"
import { getSuvisSession } from "@/lib/suvis-session"
import { listAgents, toggleAgent, type AgentSummary } from "@/lib/admin-api"

export default function AdminAgentsPage() {
  const router = useRouter()
  const [agents, setAgents] = useState<AgentSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [togglingId, setTogglingId] = useState<string | null>(null)

  useEffect(() => {
    const session = getSuvisSession()
    if (!session || session.role !== "admin") {
      router.replace("/")
      return
    }
    listAgents()
      .then(setAgents)
      .catch((e: Error) => setError(e.message))
  }, [router])

  const handleToggle = async (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setTogglingId(id)
    try {
      const { status } = await toggleAgent(id)
      setAgents((prev) => prev?.map((a) => (a.id === id ? { ...a, status } : a)) ?? null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "토글에 실패했습니다.")
    } finally {
      setTogglingId(null)
    }
  }

  return (
    <div className="min-h-screen">
      <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <AdminMenuButton />
          <div>
            <h1 className="text-base font-bold text-slate-800 md:text-lg">에이전트 관리</h1>
            <p className="text-xs text-slate-400">멀티에이전트 상태·토글·테스트 호출</p>
          </div>
        </div>
      </header>

      <div className="p-4 md:p-6 lg:p-8">
        {error && (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
            {error}
          </p>
        )}

        {!agents ? (
          <div className="flex items-center justify-center py-20 text-sm text-slate-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            불러오는 중...
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {agents.map((agent) => (
              <Link
                key={agent.id}
                href={`/admin/agents/${agent.id}`}
                className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-white p-4 transition-colors hover:border-slate-300"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-800">{agent.name}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      agent.status === "on"
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {agent.status === "on" ? "ON" : "OFF"}
                  </span>
                </div>
                <p className="line-clamp-2 text-sm text-slate-500">{agent.description}</p>
                <div className="mt-1 flex items-center justify-between">
                  <button
                    type="button"
                    disabled={togglingId === agent.id}
                    onClick={(e) => void handleToggle(agent.id, e)}
                    className="flex h-8 items-center gap-1.5 rounded-full border border-slate-300 px-3 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50"
                  >
                    {togglingId === agent.id && <Loader2 className="h-3 w-3 animate-spin" />}
                    {agent.status === "on" ? "끄기" : "켜기"}
                  </button>
                  <span className="flex items-center gap-0.5 text-xs text-slate-400">
                    상세 <ChevronRight className="h-3.5 w-3.5" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
