"use client"

import { useRef, useState } from "react"
import { Bot, CheckCircle2, CornerDownLeft, Loader2, Send } from "lucide-react"
import { EmailAutocomplete } from "@/components/mail/email-autocomplete"
import { patchState } from "@/lib/form-status"
import { authHeader } from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

type SendState = { loading: boolean; error: string | null; result: { to: string; subject: string } | null }
type DispatchEmailResponse = { success?: boolean; to?: string; subject?: string; detail?: string }

const initial: SendState = { loading: false, error: null, result: null }

export default function AdminMailPage() {
  const [state, setState] = useState<SendState>(initial)
  const [toEmail, setToEmail] = useState("")
  const toEmailRef = useRef("")
  const loadingRef = useRef(false)
  const subjectRef = useRef<HTMLInputElement>(null)
  const promptRef = useRef<HTMLTextAreaElement>(null)

  const patch = (p: Partial<SendState>) => {
    if ("loading" in p) loadingRef.current = p.loading ?? false
    patchState(setState, p)
  }

  const updateToEmail = (v: string) => { toEmailRef.current = v; setToEmail(v) }

  const handleSend = async () => {
    const to = toEmailRef.current.trim()
    const prompt = promptRef.current?.value.trim() ?? ""
    if (loadingRef.current) return
    const subject = subjectRef.current?.value.trim() || undefined
    if (!to) { patch({ error: "수신자 이메일을 입력해 주세요.", result: null }); return }
    if (!prompt) { patch({ error: "메일 내용 지시를 입력해 주세요.", result: null }); return }
    patch({ loading: true, error: null, result: null })
    try {
      const res = await fetch("/api/dispatch/email", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ to, subject, prompt }),
      })
      const data = await res.json() as DispatchEmailResponse
      if (!res.ok) throw new Error(data.detail ?? `발송 실패 (${res.status})`)
      patch({ result: { to: data.to ?? to, subject: data.subject ?? "메일 발송" }, loading: false })
    } catch (err) {
      patch({ error: err instanceof Error ? err.message : "오류가 발생했습니다.", loading: false })
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_240px]">
      <div className="overflow-hidden rounded-xl border border-slate-200">
        <div className="relative overflow-hidden bg-gradient-to-br from-indigo-700 via-indigo-800 to-indigo-900 px-6 py-5">
          <div aria-hidden className="pointer-events-none absolute right-6 top-1/2 -translate-y-1/2 opacity-[0.06]">
            <Send className="size-24 text-white" />
          </div>
          <div className="relative flex items-center gap-4">
            <div className="flex size-14 shrink-0 items-center justify-center rounded-full bg-white/10 ring-2 ring-white/20">
              <Send className="size-7 text-indigo-200" aria-hidden />
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-indigo-300/80">Powered by Exaone 3.5</p>
              <h2 className="mt-0.5 text-lg font-bold text-white">AI 메일 발송</h2>
              <p className="text-sm text-indigo-200">AI가 메일 본문을 작성하여 발송</p>
            </div>
          </div>
        </div>

        {state.result && (
          <div className="flex items-start gap-3 border-b border-emerald-200 bg-emerald-50 px-5 py-4">
            <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-500" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-emerald-800">발송 완료</p>
              <p className="mt-0.5 text-xs text-emerald-700">
                <span className="font-medium">{state.result.to}</span>에게 &ldquo;{state.result.subject}&rdquo; 발송됨
              </p>
            </div>
            <button type="button" onClick={() => patch({ result: null })} className="text-emerald-500 hover:text-emerald-700">✕</button>
          </div>
        )}
        {state.error && (
          <p className="border-b border-rose-200 bg-rose-50 px-5 py-2.5 text-xs text-rose-700">{state.error}</p>
        )}
        {state.loading && (
          <div className="border-b border-indigo-200 bg-indigo-50 px-5 py-3">
            <div className="flex items-center gap-3">
              <Loader2 className="size-4 animate-spin text-indigo-500" />
              <p className="text-xs font-medium text-indigo-700">엑사원이 메일 본문을 작성하고 있습니다… 최대 20초 정도 걸릴 수 있어요.</p>
            </div>
          </div>
        )}

        <form onSubmit={(e) => { e.preventDefault(); void handleSend() }} className="space-y-4 bg-slate-50 p-5">
          <div>
            <label htmlFor="admin-mail-to" className="block text-xs font-semibold text-slate-700">
              수신자 이메일 <span className="text-rose-500">*</span>
            </label>
            <EmailAutocomplete value={toEmail} onChange={updateToEmail} disabled={state.loading} />
          </div>
          <div>
            <label htmlFor="admin-mail-subject" className="block text-xs font-semibold text-slate-700">
              제목 <span className="text-slate-400 font-normal">(선택)</span>
            </label>
            <input
              ref={subjectRef}
              id="admin-mail-subject"
              type="text"
              placeholder="비우면 기본값 적용"
              disabled={state.loading}
              className={cn(
                "mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm",
                "placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-200",
                "disabled:opacity-50",
              )}
            />
          </div>
          <div>
            <label htmlFor="admin-mail-prompt" className="block text-xs font-semibold text-slate-700">
              내용 지시 <span className="text-rose-500">*</span>
            </label>
            <textarea
              ref={promptRef}
              id="admin-mail-prompt"
              rows={5}
              placeholder="예: 내일 오전 미팅 일정을 확인하는 짧은 메일을 친근하게 써줘"
              disabled={state.loading}
              className={cn(
                "mt-1.5 w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm",
                "placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-200",
                "disabled:opacity-50",
              )}
            />
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={state.loading}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600 disabled:opacity-50"
            >
              {state.loading ? <><Loader2 className="size-4 animate-spin" />발송 중…</> : <><CornerDownLeft className="size-4" />발송</>}
            </button>
          </div>
        </form>
      </div>

      <aside className="space-y-4">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
          <div className="border-b border-slate-200 px-4 py-3">
            <p className="text-sm font-semibold text-slate-800">파이프라인</p>
          </div>
          <div className="space-y-3 p-4 text-center text-slate-700">
            <div>
              <Bot className="mx-auto size-7 text-indigo-500" />
              <p className="mt-1 text-sm font-semibold">Exaone 3.5</p>
              <p className="text-xs text-slate-500">본문 작성</p>
            </div>
            <div className="mx-auto h-4 w-px bg-slate-200" aria-hidden />
            <div>
              <Send className="mx-auto size-7 text-emerald-500" />
              <p className="mt-1 text-sm font-semibold">n8n → Gmail</p>
              <p className="text-xs text-slate-500">실제 발송</p>
            </div>
          </div>
        </div>
      </aside>
    </div>
  )
}
