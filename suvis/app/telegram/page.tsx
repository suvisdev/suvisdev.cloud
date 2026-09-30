"use client"

import Link from "next/link"
import { useRef, useState } from "react"
import { Bot, CheckCircle2, CornerDownLeft, Loader2, Send, Smartphone } from "lucide-react"
import { patchState } from "@/lib/form-status"
import { cn } from "@/lib/utils"

type SendState = {
  loading: boolean
  error: string | null
  sent: boolean
}

const initial: SendState = { loading: false, error: null, sent: false }

type DispatchTelegramResponse = {
  success?: boolean
  detail?: string
}

export default function TelegramPage() {
  const [state, setState] = useState<SendState>(initial)
  const patch = (p: Partial<SendState>) => patchState(setState, p)

  const messageRef = useRef<HTMLTextAreaElement>(null)
  const chatIdRef = useRef<HTMLInputElement>(null)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (state.loading) return

    const message = messageRef.current?.value.trim() ?? ""
    const chatId = chatIdRef.current?.value.trim() || undefined

    if (!message) {
      patch({ error: "보낼 메시지를 입력해 주세요.", sent: false })
      return
    }

    patch({ loading: true, error: null, sent: false })

    try {
      const res = await fetch("/api/dispatch/telegram", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, chat_id: chatId }),
      })
      const data = (await res.json()) as DispatchTelegramResponse
      if (!res.ok || !data.success) {
        throw new Error(data.detail ?? `전송 실패 (${res.status})`)
      }
      patch({ sent: true, loading: false })
      if (messageRef.current) messageRef.current.value = ""
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
            텔레그램 알림
          </h1>
          <p className="mt-5 max-w-3xl text-sm leading-7 text-neutral-600 md:text-base dark:text-neutral-400">
            메시지를 입력하면 봇이 내 텔레그램으로 즉시 전송합니다.
          </p>

          <div className="mt-8 grid gap-4 lg:grid-cols-[1fr_240px]">
            {/* 폼 카드 */}
            <div className="overflow-hidden rounded-xl border border-neutral-200 dark:border-[#252b3b]">
              {/* 헤더 */}
              <div className="relative overflow-hidden bg-gradient-to-br from-sky-600 via-sky-700 to-sky-900 px-6 py-5">
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
                  <Send className="size-24 text-white" />
                </div>
                <div className="relative flex items-center gap-4">
                  <div className="flex size-14 shrink-0 items-center justify-center rounded-full bg-white/10 ring-2 ring-white/20 backdrop-blur-sm">
                    <Send className="size-7 text-sky-100" aria-hidden />
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold tracking-[0.2em] text-sky-200/80 uppercase">
                      Powered by Telegram Bot API
                    </p>
                    <h2 className="mt-0.5 text-lg font-bold text-white">텔레그램 발송</h2>
                    <p className="text-sm text-sky-200">봇이 내 폰으로 메시지를 전송</p>
                  </div>
                </div>
              </div>

              {/* 성공 */}
              {state.sent && (
                <div className="flex items-start gap-3 border-b border-emerald-200 bg-emerald-50 px-5 py-4 dark:border-emerald-900/30 dark:bg-emerald-950/20">
                  <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-500" aria-hidden />
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">
                      전송 완료
                    </p>
                    <p className="mt-0.5 text-xs text-emerald-700 dark:text-emerald-400">
                      텔레그램으로 메시지를 전송했습니다.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => patch({ sent: false })}
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

              {/* 폼 */}
              <form
                onSubmit={handleSubmit}
                className="space-y-4 bg-neutral-50 p-5 dark:bg-[#0d0f14]"
              >
                <div>
                  <label
                    htmlFor="tg-message"
                    className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300"
                  >
                    메시지 내용 <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    ref={messageRef}
                    id="tg-message"
                    rows={5}
                    placeholder="예: 홍길동에게 메일을 정상적으로 발송했습니다."
                    disabled={state.loading}
                    className={cn(
                      "mt-1.5 w-full resize-none rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900",
                      "placeholder:text-neutral-400 focus:border-sky-400 focus:ring-1 focus:ring-sky-200 focus:outline-none",
                      "disabled:opacity-50 dark:border-[#252b3b] dark:bg-[#161a24] dark:text-neutral-100 dark:placeholder:text-neutral-600"
                    )}
                  />
                </div>

                <div>
                  <label
                    htmlFor="tg-chat-id"
                    className="block text-xs font-semibold text-neutral-700 dark:text-neutral-300"
                  >
                    Chat ID <span className="font-normal text-neutral-400">(선택)</span>
                  </label>
                  <input
                    ref={chatIdRef}
                    id="tg-chat-id"
                    type="text"
                    placeholder="비우면 기본 수신자(.env)로 전송"
                    disabled={state.loading}
                    className={cn(
                      "mt-1.5 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900",
                      "placeholder:text-neutral-400 focus:border-sky-400 focus:ring-1 focus:ring-sky-200 focus:outline-none",
                      "disabled:opacity-50 dark:border-[#252b3b] dark:bg-[#161a24] dark:text-neutral-100 dark:placeholder:text-neutral-600"
                    )}
                  />
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={state.loading}
                    className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {state.loading ? (
                      <>
                        <Loader2 className="size-4 animate-spin" aria-hidden />
                        전송 중…
                      </>
                    ) : (
                      <>
                        <CornerDownLeft className="size-4" aria-hidden />
                        전송
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
                    <Bot className="mx-auto size-7 text-sky-500" />
                    <p className="mt-1 text-sm font-semibold">FastAPI</p>
                    <p className="text-xs text-neutral-500">발송 요청</p>
                  </div>
                  <div className="mx-auto h-4 w-px bg-neutral-200 dark:bg-[#252b3b]" aria-hidden />
                  <div>
                    <Smartphone className="mx-auto size-7 text-emerald-500" />
                    <p className="mt-1 text-sm font-semibold">Telegram Bot</p>
                    <p className="text-xs text-neutral-500">내 폰 알림</p>
                  </div>
                </div>
              </div>

              <article className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-sm leading-6 text-neutral-600 dark:border-[#252b3b] dark:bg-[#1a1f2d] dark:text-neutral-400">
                <p className="font-semibold text-neutral-900 dark:text-neutral-100">사용 안내</p>
                <ul className="mt-2 space-y-1.5 text-xs leading-5">
                  <li>· 봇 토큰·Chat ID는 서버 .env에 저장</li>
                  <li>· Chat ID 미입력 시 기본 수신자로 전송</li>
                  <li>· 봇에게 먼저 /start를 눌러야 수신 가능</li>
                </ul>
              </article>
            </aside>
          </div>
        </section>
      </main>
    </div>
  )
}
