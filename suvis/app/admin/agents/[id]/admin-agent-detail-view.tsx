"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { ArrowLeft, Loader2, Play } from "lucide-react"
import { AdminMenuButton } from "../../_components/admin-menu-button"
import { getSuvisSession } from "@/lib/suvis-session"
import {
  getAgent,
  getAgentLogs,
  invokeAgent,
  toggleAgent,
  type AgentDetail,
  type AgentLogEntry,
} from "@/lib/admin-api"

export function AdminAgentDetailView({ id }: { id: string }) {
  const router = useRouter()
  const [agent, setAgent] = useState<AgentDetail | null>(null)
  const [logs, setLogs] = useState<AgentLogEntry[]>([])
  const [error, setError] = useState<string | null>(null)
  const [toggling, setToggling] = useState(false)
  const [invoking, setInvoking] = useState(false)
  const [invokeResult, setInvokeResult] = useState<string | null>(null)

  const load = useCallback(() => {
    Promise.all([getAgent(id), getAgentLogs(id)])
      .then(([a, l]) => {
        setAgent(a)
        setLogs(l)
      })
      .catch((e: Error) => setError(e.message))
  }, [id])

  useEffect(() => {
    const session = getSuvisSession()
    if (!session || session.role !== "admin") {
      router.replace("/")
      return
    }
    load()
  }, [router, load])

  const handleToggle = async () => {
    setToggling(true)
    try {
      const { status } = await toggleAgent(id)
      setAgent((prev) => (prev ? { ...prev, status } : prev))
    } catch (e) {
      setError(e instanceof Error ? e.message : "토글에 실패했습니다.")
    } finally {
      setToggling(false)
    }
  }

  const handleInvoke = async () => {
    setInvoking(true)
    setInvokeResult(null)
    try {
      const { result } = await invokeAgent(id)
      setInvokeResult(result)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : "테스트 호출에 실패했습니다.")
    } finally {
      setInvoking(false)
    }
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 text-center">
        <p className="text-sm font-medium text-red-600">{error}</p>
        <Link href="/admin/agents" className="text-sm text-slate-500 underline underline-offset-2">
          목록으로 돌아가기
        </Link>
      </div>
    )
  }

  if (!agent) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-400">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        불러오는 중...
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <AdminMenuButton />
          <div>
            <h1 className="text-base font-bold text-slate-800 md:text-lg">{agent.name}</h1>
            <p className="text-xs text-slate-400">{agent.description}</p>
          </div>
        </div>
      </header>

      <div className="p-4 md:p-6 lg:p-8">
        <Link
          href="/admin/agents"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          목록으로
        </Link>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-800">상태 · 모델</h2>
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
            <p className="mt-3 text-sm text-slate-600">
              <span className="text-slate-400">모델: </span>
              {agent.model}
            </p>
            <div className="mt-4 flex gap-2">
              <button
                type="button"
                disabled={toggling}
                onClick={() => void handleToggle()}
                className="flex h-9 items-center gap-1.5 rounded-full border border-slate-300 px-4 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50"
              >
                {toggling && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                {agent.status === "on" ? "끄기" : "켜기"}
              </button>
              <button
                type="button"
                disabled={invoking}
                onClick={() => void handleInvoke()}
                className="flex h-9 items-center gap-1.5 rounded-full bg-emerald-600 px-4 text-xs font-medium text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
              >
                {invoking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                테스트 호출
              </button>
            </div>
            {invokeResult && (
              <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
                {invokeResult}
              </p>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-slate-800">로그</h2>
            <div className="mt-3 space-y-2">
              {logs.length === 0 && <p className="text-xs text-slate-400">로그가 없습니다.</p>}
              {logs.map((log, i) => (
                <div key={i} className="rounded-lg bg-slate-50 px-3 py-2 text-xs">
                  <span className="text-slate-400">{log.timestamp}</span>
                  <p className="mt-0.5 text-slate-700">{log.message}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
