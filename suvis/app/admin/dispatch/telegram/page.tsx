"use client"

import { useRef, useState } from "react"
import { Bot, CheckCircle2, CornerDownLeft, Loader2, Send, Smartphone } from "lucide-react"
import { patchState } from "@/lib/form-status"
import { cn } from "@/lib/utils"

type SendState = { loading: boolean; error: string | null; sent: boolean }
type DispatchTelegramResponse = { success?: boolean; detail?: string }

const initial: SendState = { loading: false, error: null, sent: false }

export default function AdminTelegramPage() {
  const [state, setState] = useState<SendState>(initial)
  const patch = (p: Partial<SendState>) => patchState(setState, p)
  const messageRef = useRef<HTMLTextAreaElement>(null)
  const chatIdRef = useRef<HTMLInputElement>(null)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (state.loading) return
    const message = messageRef.current?.value.trim() ?? ""
    const chatId = chatIdRef.current?.value.trim() || undefined
    if (!message) { patch({ error: "보낼 메시지를 입력해 주세요.", sent: false }); return }
    patch({ loading: true, error: null, sent: false })
    try {
      const res = await fetch("/api/dispatch/telegram", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, chat_id: chatId }),
      })
      const data = await res.json() as DispatchTelegramResponse
      if (!res.ok || !data.success) throw new Error(data.detail ?? `전송 실패 (${res.status})`)
      patch({ sent: true, loading: false })
      if (messageRef.current) messageRef.current.value = ""
    } catch (err) {
      patch({ error: err instanceof Error ? err.message : "오류가 발생했습니다.", loading: false })
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_240px]">
      <div className="overflow-hidden rounded-xl border border-slate-200">
        <div className="relative overflow-hidden bg-gradient-to-br from-sky-600 via-sky-700 to-sky-900 px-6 py-5">
          <div aria-hidden className="pointer-events-none absolute right-6 top-1/2 -translate-y-1/2 opacity-[0.06]">
            <Send className="size-24 text-white" />
          </div>
          <div className="relative flex items-center gap-4">
            <div className="flex size-14 shrink-0 items-center justify-center rounded-full bg-white/10 ring-2 ring-white/20">
              <Send className="size-7 text-sky-100" aria-hidden />
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-sky-200/80">Powered by Telegram Bot API</p>
              <h2 className="mt-0.5 text-lg font-bold text-white">텔레그램 발송</h2>
              <p className="text-sm text-sky-200">봇이 내 폰으로 메시지를 전송</p>
            </div>
          </div>
        </div>

        {state.sent && (
          <div className="flex items-start gap-3 border-b border-emerald-200 bg-emerald-50 px-5 py-4">
            <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-500" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-emerald-800">전송 완료</p>
              <p className="mt-0.5 text-xs text-emerald-700">텔레그램으로 메시지를 전송했습니다.</p>
            </div>
            <button type="button" onClick={() => patch({ sent: false })} className="text-emerald-500 hover:text-emerald-700">✕</button>
          </div>
        )}
        {state.error && (
          <p className="border-b border-rose-200 bg-rose-50 px-5 py-2.5 text-xs text-rose-700">{state.error}</p>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 bg-slate-50 p-5">
          <div>
            <label htmlFor="admin-tg-message" className="block text-xs font-semibold text-slate-700">
              메시지 내용 <span className="text-rose-500">*</span>
            </label>
            <textarea
              ref={messageRef}
              id="admin-tg-message"
              rows={5}
              placeholder="예: 홍길동에게 메일을 정상적으로 발송했습니다."
              disabled={state.loading}
              className={cn(
                "mt-1.5 w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm",
                "placeholder:text-slate-400 focus:border-sky-400 focus:outline-none focus:ring-1 focus:ring-sky-200",
                "disabled:opacity-50",
              )}
            />
          </div>
          <div>
            <label htmlFor="admin-tg-chat-id" className="block text-xs font-semibold text-slate-700">
              Chat ID <span className="text-slate-400 font-normal">(선택)</span>
            </label>
            <input
              ref={chatIdRef}
              id="admin-tg-chat-id"
              type="text"
              placeholder="비우면 기본 수신자(.env)로 전송"
              disabled={state.loading}
              className={cn(
                "mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm",
                "placeholder:text-slate-400 focus:border-sky-400 focus:outline-none focus:ring-1 focus:ring-sky-200",
                "disabled:opacity-50",
              )}
            />
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={state.loading}
              className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
            >
              {state.loading ? <><Loader2 className="size-4 animate-spin" />전송 중…</> : <><CornerDownLeft className="size-4" />전송</>}
            </button>
          </div>
        </form>
      </div>

      <aside className="space-y-4">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
          <div className="border-b border-slate-200 px-4 py-3">
            <p className="text-sm font-semibold text-slate-800">파이프라인</p>
          </div>
          <div className="space-y-3 p-4 text-center">
            <div>
              <Bot className="mx-auto size-7 text-sky-500" />
              <p className="mt-1 text-sm font-semibold">FastAPI</p>
              <p className="text-xs text-slate-500">발송 요청</p>
            </div>
            <div className="mx-auto h-4 w-px bg-slate-200" aria-hidden />
            <div>
              <Smartphone className="mx-auto size-7 text-emerald-500" />
              <p className="mt-1 text-sm font-semibold">Telegram Bot</p>
              <p className="text-xs text-slate-500">내 폰 알림</p>
            </div>
          </div>
        </div>
      </aside>
    </div>
  )
}
