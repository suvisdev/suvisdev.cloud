"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { Cpu, Loader2, Power, Server, Zap } from "lucide-react"
import { getOps, postOps, type OpsStatus } from "@/lib/admin-dashboard-api"

// 버튼이 보내는 동작 → 화면에 보일 이름
const ACTION_LABEL: Record<string, string> = {
  "/arda/start": "Arda 켜기",
  "/arda/stop": "Arda 끄기",
  "/arda/ai-mode": "Arda AI 전환",
  "/ollama/load": "모델 올리기",
  "/ollama/unload": "모델 내리기",
}

const FAST_POLL_MS = 3_000 // 동작이 도는 동안
const SLOW_POLL_MS = 30_000 // 평소

function gib(mib: number) {
  return `${(mib / 1024).toFixed(1)}GB`
}

/** 운영 제어 — 노트북 Arda 켜기·끄기, Arda AI GPU·CPU, Ollama 모델 GPU 올리기·내리기.
 *  동작은 접수만 하고 바로 돌아오므로(1~3분 걸리는 일도 있음) job 상태를 짧은 간격으로 다시 읽는다. */
export function OpsControlCard() {
  const [ops, setOps] = useState<OpsStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const refresh = useCallback(async () => {
    try {
      const next = await getOps()
      setOps(next)
      setError(null)
      return next
    } catch (e) {
      setError((e as Error).message)
      return null
    }
  }, [])

  // job 이 도는 동안엔 3초, 평소엔 30초마다
  useEffect(() => {
    let alive = true
    const loop = async () => {
      const next = await refresh()
      if (!alive) return
      const running = next?.job?.state === "running"
      timer.current = setTimeout(loop, running ? FAST_POLL_MS : SLOW_POLL_MS)
    }
    loop()
    return () => {
      alive = false
      if (timer.current) clearTimeout(timer.current)
    }
  }, [refresh])

  const run = async (path: string, body?: Record<string, string>, confirmText?: string) => {
    if (confirmText && !window.confirm(confirmText)) return
    setSending(true)
    try {
      await postOps(path, body)
      setError(null)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSending(false)
    }
    // 바로 한 번 읽고, 이후엔 위 루프가 3초 간격으로 따라간다
    if (timer.current) clearTimeout(timer.current)
    const next = await refresh()
    const again = async () => {
      const s = await refresh()
      if (s?.job?.state === "running") timer.current = setTimeout(again, FAST_POLL_MS)
      else timer.current = setTimeout(again, SLOW_POLL_MS)
    }
    timer.current = setTimeout(again, next?.job?.state === "running" ? FAST_POLL_MS : SLOW_POLL_MS)
  }

  const job = ops?.job
  const busy = sending || job?.state === "running"
  const services = ops?.arda?.services ?? []
  const runningCount = services.filter((s) => s.state === "running").length
  const ardaOn = runningCount > 0
  const aiMode = ops?.arda?.ai_mode ?? "cpu"
  const aiDevice = ops?.arda?.ai_device
  const gpu = ops?.gpu?.[0]
  const loaded = new Map((ops?.ollama?.loaded ?? []).map((m) => [m.name, m]))
  const installed = ops?.ollama?.installed ?? []

  return (
    <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-bold text-slate-800">
          <Server className="h-4 w-4 text-slate-400" />
          운영 제어 · 노트북
        </h2>
        <span
          className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
            !ops
              ? "bg-slate-100 text-slate-500"
              : ops.reachable
                ? "bg-emerald-100 text-emerald-700"
                : "bg-red-100 text-red-600"
          }`}
        >
          {!ops ? "확인 중" : ops.reachable ? "연결됨" : "노트북 연결 안 됨"}
        </span>
      </div>

      {error && <p className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{error}</p>}
      {ops && !ops.reachable && (
        <p className="mb-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
          노트북 제어 에이전트에 닿지 않습니다. 노트북이 꺼져 있거나 에이전트가 멈췄을 수 있어요.
        </p>
      )}

      {job && job.state !== "idle" && (
        <p
          className={`mb-3 flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${
            job.state === "running"
              ? "bg-amber-50 text-amber-700"
              : job.state === "ok"
                ? "bg-emerald-50 text-emerald-700"
                : "bg-red-50 text-red-600"
          }`}
        >
          {job.state === "running" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          <span className="font-semibold">{ACTION_LABEL[job.action ?? ""] ?? job.action}</span>
          {job.target && <span className="text-slate-500">{job.target}</span>}
          <span>
            {job.state === "running"
              ? "진행 중… (최대 몇 분)"
              : job.state === "ok"
                ? "완료"
                : `실패: ${job.error ?? ""}`}
          </span>
        </p>
      )}

      {ops?.reachable && (
        <div className="grid gap-3 lg:grid-cols-2">
          {/* Arda */}
          <div className="rounded-xl bg-slate-50 px-4 py-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-xs font-semibold text-slate-800">Arda (팀 프로젝트)</p>
              <span className="text-xs text-slate-500">
                {ops.arda?.available
                  ? `컨테이너 ${runningCount}/${services.length} 동작`
                  : "상태 확인 실패"}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy || ardaOn}
                onClick={() => run("/arda/start")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
              >
                <Power className="h-3.5 w-3.5" /> 켜기
              </button>
              <button
                type="button"
                disabled={busy || !ardaOn}
                onClick={() =>
                  run(
                    "/arda/stop",
                    undefined,
                    "Arda 를 끕니다. seuk.suvisdev.cloud 에서 로그인이 안 됩니다. 계속할까요?"
                  )
                }
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-40"
              >
                <Power className="h-3.5 w-3.5" /> 끄기
              </button>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-xs text-slate-500">AI 면접(음성 인식·표정)</span>
              <div className="inline-flex overflow-hidden rounded-lg border border-slate-300 text-xs font-semibold">
                {(["cpu", "gpu"] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    disabled={busy || !ardaOn || aiMode === mode}
                    onClick={() => run("/arda/ai-mode", { mode })}
                    className={`inline-flex items-center gap-1 px-3 py-1.5 disabled:cursor-default ${
                      aiMode === mode
                        ? "bg-slate-800 text-white"
                        : "bg-white text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                    }`}
                  >
                    {mode === "gpu" ? (
                      <Zap className="h-3.5 w-3.5" />
                    ) : (
                      <Cpu className="h-3.5 w-3.5" />
                    )}
                    {mode.toUpperCase()}
                  </button>
                ))}
              </div>
              {aiDevice && aiDevice !== (aiMode === "gpu" ? "cuda" : "cpu") && (
                <span className="text-[11px] text-amber-600">실제: {aiDevice}</span>
              )}
            </div>
          </div>

          {/* GPU · 모델 */}
          <div className="rounded-xl bg-slate-50 px-4 py-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="truncate text-xs font-semibold text-slate-800">
                {gpu ? gpu.name.replace("NVIDIA GeForce ", "") : "GPU"}
              </p>
              {gpu && (
                <span className="shrink-0 text-xs text-slate-500">
                  {gib(gpu.memory_used_mib)} / {gib(gpu.memory_total_mib)} · {gpu.utilization_pct}%
                </span>
              )}
            </div>
            {gpu && (
              <div className="mb-3 h-1.5 overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-violet-500"
                  style={{
                    width: `${Math.min(100, (gpu.memory_used_mib / gpu.memory_total_mib) * 100)}%`,
                  }}
                />
              </div>
            )}
            {!ops.ollama?.available ? (
              <p className="text-xs text-slate-400">Ollama 상태를 읽지 못했습니다.</p>
            ) : (
              <ul className="space-y-1.5">
                {installed.map((name) => {
                  const m = loaded.get(name)
                  return (
                    <li key={name} className="flex items-center justify-between gap-2 text-xs">
                      <span className="min-w-0 truncate text-slate-700">
                        {name}
                        {m && (
                          <span className="ml-1.5 rounded-full bg-violet-100 px-1.5 py-0.5 text-[10px] font-semibold text-violet-700">
                            GPU{m.size_vram ? ` ${gib(m.size_vram / 1024 / 1024)}` : ""}
                          </span>
                        )}
                      </span>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => run(m ? "/ollama/unload" : "/ollama/load", { model: name })}
                        className="shrink-0 rounded-md border border-slate-300 bg-white px-2 py-0.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                      >
                        {m ? "내리기" : "올리기"}
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
