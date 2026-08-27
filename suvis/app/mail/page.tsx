"use client"

import Link from "next/link"
import { useRef, useState } from "react"
import { Bot, CheckCircle2, CornerDownLeft, Loader2, Mail, Send } from "lucide-react"
import { EmailAutocomplete } from "@/components/mail/email-autocomplete"
import { patchState } from "@/lib/form-status"
import { authHeader } from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

type SendState = {
  loading: boolean
  error: string | null
  result: { to: string; subject: string } | null
}

const initial: SendState = { loading: false, error: null, result: null }

type DispatchEmailResponse = {
  success?: boolean
  to?: string
  subject?: string
  detail?: string
}

export default function MailPage() {
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

  const updateToEmail = (v: string) => {
    toEmailRef.current = v
    setToEmail(v)
  }

  const handleSend = async () => {
    const to = toEmailRef.current.trim()
    const prompt = promptRef.current?.value.trim() ?? ""

    if (loadingRef.current) return

    const subject = subjectRef.current?.value.trim() || undefined

    if (!to) {
      patch({ error: "수신자 이메일을 입력해 주세요.", result: null })
      return
    }
    if (!prompt) {
      patch({ error: "메일 내용 지시를 입력해 주세요.", result: null })
      return
    }

    patch({ loading: true, error: null, result: null })

    try {
      const res = await fetch("/api/dispatch/email", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ to, subject, prompt }),
      })
      const data = (await res.json()) as DispatchEmailResponse
      if (!res.ok) throw new Error(data.detail ?? `발송 실패 (${res.status})`)
      patch({ result: { to: data.to ?? to, subject: data.subject ?? "메일 발송" }, loading: false })
    } catch (err) {
      patch({ error: err instanceof Error ? err.message : "오류가 발생했습니다.", loading: false })
    }
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[#f3f3f3] px-4 py-4 md:px-6 md:py-6 dark:bg-[#0d0f14]">
      <main className="mx-auto grid max-w-[1500px] gap-4 md:grid-cols-[220px_1fr]">
        {/* 사이드바 */}
        <aside className="rounded-xl border border-neutral-200 bg-white p-4 dark:border-[#252b3b] dark:bg-[#161a24]">
          <p className="text-xs font-semibold tracking-wide text-neutral-500">수업명</p>
          <div className="mt-4 space-y-2">
            <Link
              href="/lesson"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              LESSON 홈
            </Link>
            <Link
              href="/titanic"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              타이타닉
            </Link>
            <Link
              href="/titanic/data-collection"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              1. 데이터 수집
            </Link>
            <Link
              href="/titanic/passengers"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              2. 승객목록
            </Link>
            <Link
              href="/titanic/smith-captain"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              3. 스미스 선장과 대화
            </Link>
          </div>
          <p className="mt-6 text-xs font-semibold tracking-wide text-neutral-500">VISION</p>
          <div className="mt-2 space-y-2">
            <Link
              href="/vision"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              이미지 업로드
            </Link>
            <Link
              href="/vision/object-detection"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              객체 탐지
            </Link>
          </div>
          <p className="mt-6 text-xs font-semibold tracking-wide text-neutral-500">SOCCER</p>
          <div className="mt-2 space-y-2">
            <Link
              href="/soccer/chat"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              채팅
            </Link>
          </div>
          <p className="mt-6 text-xs font-semibold tracking-wide text-neutral-500">LANGCHAIN</p>
          <div className="mt-2 space-y-2">
            <Link
              href="/langchain/chat"
              className="block rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-[#252b3b]"
            >
              채팅
            </Link>
          </div>
        </aside>

        {/* 메인 */}
        <section className="rounded-xl border border-neutral-200 bg-white p-6 md:p-8 dark:border-[#252b3b] dark:bg-[#161a24]">
          <p className="text-xs font-semibold tracking-[0.2em] text-neutral-500">DISPATCH</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
            메일 발송
          </h1>
          <p className="mt-5 max-w-3xl text-sm leading-7 text-neutral-600 md:text-base dark:text-neutral-400">
            수신자와 내용 지시를 입력하면 엑사원이 메일 본문을 작성해 발송합니다.
          </p>

          <div className="mt-8 grid gap-4 lg:grid-cols-[1fr_240px]">
            {/* 폼 카드 */}
            <div className="overflow-hidden rounded-xl border border-neutral-200 dark:border-[#252b3b]">
              {/* 헤더 */}
              <div className="relative overflow-hidden bg-gradient-to-br from-indigo-700 via-indigo-800 to-indigo-900 px-6 py-5">
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0 opacity-[0.07]"
                  style={{
                    backgroundImage:
                      "repeating-linear-gradient(135deg, transparent, transparent 18px, rgba(255,255,255,0.6) 18px, rgba(255,255,255,0.6) 19px)",
                  }}
                />
                <div
                  aria-hidden
                  className="pointer-events-none absolute top-1/2 right-6 -translate-y-1/2 opacity-[0.06]"
                >
                  <Mail className="size-24 text-white" />
                </div>
                <div className="relative flex items-center gap-4">
                  <div className="flex size-14 shrink-0 items-center justify-center rounded-full bg-white/10 ring-2 ring-white/20 backdrop-blur-sm">
                    <Send className="size-7 text-indigo-200" aria-hidden />
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold tracking-[0.2em] text-indigo-300/80 uppercase">
                      Powered by Exaone 3.5
                    </p>
                    <h2 className="mt-0.5 text-lg font-bold text-white">AI 메일 발송</h2>
                    <p className="text-sm text-indigo-200">AI가 메일 본문을 작성하여 발송</p>
                  </div>
                </div>
              </div>

              {/* 성공 */}
              {state.result && (
                <div className="flex items-start gap-3 border-b border-emerald-200 bg-emerald-50 px-5 py-4 dark:border-emerald-900/30 dark:bg-emerald-950/20">
                  <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-500" aria-hidden />
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">
                      발송 완료
                    </p>
                    <p className="mt-0.5 text-xs text-emerald-700 dark:text-emerald-400">
                      <span className="font-medium">{state.result.to}</span>에게 &ldquo;
                      {state.result.subject}&rdquo; 발송됨
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => patch({ result: null })}
                    className="ml-2 text-emerald-500 hover:text-emerald-700 dark:text-emerald-400 dark:hover:text-emerald-200"
                    aria-label="닫기"
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* 오류 */}
              {state.error && (
                <p className="border-b border-rose-200 bg-rose-50 px-5 py-2.5 text-xs text-rose-700 dark:border-rose-900/30 dark:bg-rose-950/20 dark:text-rose-400">
                  {state.error}
                </p>
              )}

              {/* 진행 중 */}
              {state.loading && (
                <div className="border-b border-indigo-200 bg-indigo-50 px-5 py-3 dark:border-indigo-900/30 dark:bg-indigo-950/20">
                  <div className="flex items-center gap-3">
                    <Loader2 className="size-4 shrink-0 animate-spin text-indigo-500" aria-hidden />
                    <p className="text-xs font-medium text-indigo-700 dark:text-indigo-300">
                      엑사원이 메일 본문을 작성하고 있습니다… 최대 20초 정도 걸릴 수 있어요.
                    </p>
                  </div>
                  <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-indigo-100 dark:bg-indigo-900/40">
                    <div className="h-full w-1/3 animate-pulse rounded-full bg-indigo-500" />
                  </div>
                </div>
              )}

              {/* 폼 */}
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  void handleSend()
                }}
                className="space-y-4 bg-neutral-50 p-5 dark:bg-[#0d0f14]"
              >
                <div>
                  <label
                    htmlFor="mail-to"
                    className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300"
                  >
                    수신자 이메일 <span className="text-rose-500">*</span>
                  </label>
                  <EmailAutocomplete
                    value={toEmail}
                    onChange={updateToEmail}
                    disabled={state.loading}
                  />
                </div>

                <div>
                  <label
                    htmlFor="mail-subject"
                    className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300"
                  >
                    제목 <span className="font-normal text-neutral-400">(선택)</span>
                  </label>
                  <input
                    ref={subjectRef}
                    id="mail-subject"
                    type="text"
                    placeholder="비우면 기본값 적용"
                    disabled={state.loading}
                    className={cn(
                      "mt-1.5 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900",
                      "placeholder:text-neutral-400 focus:border-indigo-400 focus:ring-1 focus:ring-indigo-200 focus:outline-none",
                      "disabled:opacity-50 dark:border-[#252b3b] dark:bg-[#161a24] dark:text-neutral-100 dark:placeholder:text-neutral-600"
                    )}
                  />
                </div>

                <div>
                  <label
                    htmlFor="mail-prompt"
                    className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300"
                  >
                    내용 지시 <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    ref={promptRef}
                    id="mail-prompt"
                    rows={5}
                    placeholder="예: 내일 오전 미팅 일정을 확인하는 짧은 메일을 친근하게 써줘"
                    disabled={state.loading}
                    className={cn(
                      "mt-1.5 w-full resize-none rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900",
                      "placeholder:text-neutral-400 focus:border-indigo-400 focus:ring-1 focus:ring-indigo-200 focus:outline-none",
                      "disabled:opacity-50 dark:border-[#252b3b] dark:bg-[#161a24] dark:text-neutral-100 dark:placeholder:text-neutral-600"
                    )}
                  />
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={state.loading}
                    className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-600 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {state.loading ? (
                      <>
                        <Loader2 className="size-4 animate-spin" aria-hidden />
                        발송 중… (최대 20초)
                      </>
                    ) : (
                      <>
                        <CornerDownLeft className="size-4" aria-hidden />
                        발송
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>

            {/* 우측 */}
            <aside className="space-y-4">
              <div className="overflow-hidden rounded-xl border border-neutral-200 bg-neutral-50 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
                <div className="border-b border-neutral-200 px-4 py-3 dark:border-[#252b3b]">
                  <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                    파이프라인
                  </p>
                </div>
                <div className="space-y-3 p-4 text-center text-neutral-700 dark:text-neutral-300">
                  <div>
                    <Bot className="mx-auto size-7 text-indigo-500" />
                    <p className="mt-1 text-sm font-semibold">Exaone 3.5</p>
                    <p className="text-xs text-neutral-500">본문 작성</p>
                  </div>
                  <div className="mx-auto h-4 w-px bg-neutral-200 dark:bg-[#252b3b]" aria-hidden />
                  <div>
                    <Send className="mx-auto size-7 text-emerald-500" />
                    <p className="mt-1 text-sm font-semibold">n8n → Gmail</p>
                    <p className="text-xs text-neutral-500">실제 발송</p>
                  </div>
                </div>
              </div>

              <article className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-sm leading-6 text-neutral-600 dark:border-[#252b3b] dark:bg-[#1a1f2d] dark:text-neutral-400">
                <p className="font-semibold text-neutral-900 dark:text-neutral-100">학습 포인트</p>
                <ul className="mt-2 space-y-1.5 text-xs leading-5">
                  <li>· 지시(prompt)만 입력하면 AI가 본문 작성</li>
                  <li>· ontology Hub 경유 후 발송</li>
                  <li>· n8n 워크플로우로 Gmail 연동</li>
                </ul>
              </article>
            </aside>
          </div>
        </section>
      </main>
    </div>
  )
}
