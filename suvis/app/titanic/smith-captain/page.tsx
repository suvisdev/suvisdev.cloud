"use client"

import Link from "next/link"
import { useCallback, useEffect, useRef, useState } from "react"
import { Anchor, Bot, CornerDownLeft, Loader2, MessageCircle, Ship } from "lucide-react"
import { Button } from "@/components/ui/button"
import { patchState } from "@/lib/form-status"
import { authHeader } from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

type ChatMessage = {
  role: "user" | "assistant"
  content: string
}

type ChatState = {
  messages: ChatMessage[]
  loading: boolean
  error: string | null
}

const SYSTEM_PROMPT = `당신은 타이타닉호의 선장 에드워드 존 스미스(Edward John Smith)입니다.
1912년 4월, 타이타닉호가 뉴욕을 향해 처녀항해 중인 시점입니다.
승객과 선원들의 질문에 선장으로서 위엄 있고 친절하게 답해주세요.
한국어로 대화하되, 자연스러운 경우 영어 표현을 섞어 사용할 수 있습니다.
타이타닉의 역사적 사실에 기반하여 답변하세요.`

const INITIAL_MESSAGE: ChatMessage = {
  role: "assistant",
  content:
    "안녕하시오. 본인은 RMS 타이타닉의 선장 에드워드 존 스미스요. 이 처녀항해에 대해, 혹은 타이타닉에 대해 무엇이든 자유롭게 물어보시오.",
}

const initialChat: ChatState = {
  messages: [INITIAL_MESSAGE],
  loading: false,
  error: null,
}

export default function SmithCaptainChatPage() {
  const [chat, setChat] = useState<ChatState>(initialChat)
  const patchChat = (patch: Partial<ChatState>) => patchState(setChat, patch)
  const [draft, setDraft] = useState("")

  const chatRef = useRef(chat)
  chatRef.current = chat

  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const isComposingRef = useRef(false)

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" })
  }, [chat.messages, chat.loading])

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed) {
      patchChat({ error: "질문을 입력해 주세요." })
      return
    }

    const prev = chatRef.current
    if (prev.loading) return

    const nextMessages: ChatMessage[] = [...prev.messages, { role: "user", content: trimmed }]
    patchChat({ error: null, messages: nextMessages, loading: true })
    setDraft("")

    try {
      const res = await fetch(`/api/titanic/smith/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({
          messages: nextMessages,
          model: "flash",
          systemInstruction: SYSTEM_PROMPT,
        }),
      })
      const data = (await res.json()) as { reply?: string; error?: string; detail?: string }
      if (!res.ok) {
        const errMsg = data.detail || data.error || ""
        if (res.status === 429 || errMsg.includes("429") || errMsg.includes("quota"))
          throw new Error("Gemini API 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.")
        throw new Error(errMsg || `요청에 실패했습니다. (${res.status})`)
      }
      patchChat({
        messages: [
          ...nextMessages,
          {
            role: "assistant",
            content: data.reply?.trim() || "죄송하오, 다시 질문해주시오.",
          },
        ],
        loading: false,
      })
    } catch (e) {
      const msg = e instanceof Error ? e.message : "오류가 발생했습니다."
      setChat((prev) => ({
        ...prev,
        error: msg,
        messages: prev.messages.slice(0, -1),
        loading: false,
      }))
      setDraft(trimmed)
    } finally {
      inputRef.current?.focus()
    }
  }, [])

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    void sendMessage(draft)
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== "Enter" || e.shiftKey) return
    if (isComposingRef.current || e.nativeEvent.isComposing) return
    e.preventDefault()
    void sendMessage(draft)
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
              className="block rounded-md bg-neutral-100 px-3 py-2 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-200 dark:bg-[#252b3b] dark:text-neutral-100 dark:hover:bg-[#2d3447]"
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

        {/* 메인 콘텐츠 */}
        <section className="rounded-xl border border-neutral-200 bg-white p-6 md:p-8 dark:border-[#252b3b] dark:bg-[#161a24]">
          <p className="text-xs font-semibold tracking-[0.2em] text-neutral-500">LESSON</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
            스미스 선장과 대화
          </h1>
          <p className="mt-5 max-w-4xl text-sm leading-7 text-neutral-600 md:text-base dark:text-neutral-400">
            타이타닉호 선장 에드워드 존 스미스에게 자유롭게 질문하세요. Gemini AI가 선장 역할로
            답변합니다.
          </p>

          <div className="mt-8 grid gap-4 lg:grid-cols-[1fr_240px]">
            {/* 채팅 카드 */}
            <div className="overflow-hidden rounded-xl border border-neutral-200 dark:border-[#252b3b]">
              {/* 캡틴 헤더 */}
              <div className="relative overflow-hidden bg-gradient-to-br from-slate-700 via-slate-800 to-slate-900 px-6 py-5 dark:from-[#0c1628] dark:via-[#0f1e35] dark:to-[#0a1220]">
                {/* 수평선 패턴 */}
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0 opacity-[0.07]"
                  style={{
                    backgroundImage:
                      "repeating-linear-gradient(0deg, transparent, transparent 18px, rgba(255,255,255,0.6) 18px, rgba(255,255,255,0.6) 19px)",
                  }}
                />
                {/* 우측 앵커 장식 */}
                <div
                  aria-hidden
                  className="pointer-events-none absolute top-1/2 right-6 -translate-y-1/2 opacity-[0.06]"
                >
                  <Anchor className="size-24 text-white" />
                </div>

                <div className="relative flex items-center gap-4">
                  <div className="flex size-14 shrink-0 items-center justify-center rounded-full bg-white/10 ring-2 ring-white/20 backdrop-blur-sm">
                    <Anchor className="size-7 text-amber-300" aria-hidden />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[10px] font-semibold tracking-[0.2em] text-amber-300/80 uppercase">
                      RMS Titanic · 1912
                    </p>
                    <h2 className="mt-0.5 text-lg font-bold text-white">
                      Captain Edward John Smith
                    </h2>
                    <p className="text-sm text-slate-300">처녀항해 뉴욕행 · White Star Line</p>
                  </div>
                </div>
              </div>

              {/* 메시지 목록 */}
              <div
                ref={listRef}
                className="max-h-[min(52vh,420px)] min-h-[240px] space-y-4 overflow-y-auto bg-neutral-50 p-4 md:p-5 dark:bg-[#0d0f14]"
                role="log"
                aria-live="polite"
              >
                {chat.messages.map((msg, i) => (
                  <div
                    key={`${i}-${msg.role}`}
                    className={cn(
                      "flex w-full gap-2.5",
                      msg.role === "user" ? "flex-row-reverse" : "flex-row"
                    )}
                  >
                    {/* 아바타 */}
                    <div
                      className={cn(
                        "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ring-1",
                        msg.role === "user"
                          ? "bg-neutral-100 text-neutral-600 ring-neutral-200 dark:bg-[#252b3b] dark:text-neutral-400 dark:ring-[#2d3447]"
                          : "bg-slate-700 text-amber-300 ring-slate-600 dark:bg-[#0f1e35] dark:text-amber-300 dark:ring-slate-700"
                      )}
                      aria-hidden
                    >
                      {msg.role === "user" ? "나" : <Anchor className="size-3.5" />}
                    </div>

                    {/* 말풍선 */}
                    <div
                      className={cn(
                        "max-w-[82%] rounded-2xl px-4 py-2.5 text-[13px] leading-relaxed shadow-sm md:text-sm",
                        msg.role === "user"
                          ? "rounded-tr-sm border border-amber-200/60 bg-amber-50 text-neutral-900 dark:border-amber-900/30 dark:bg-amber-950/20 dark:text-neutral-100"
                          : "rounded-tl-sm border border-slate-200 bg-white text-slate-700 dark:border-slate-700/50 dark:bg-[#141c2b] dark:text-slate-200"
                      )}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}

                {chat.loading && (
                  <div className="flex gap-2.5">
                    <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-slate-700 text-amber-300 ring-1 ring-slate-600 dark:bg-[#0f1e35] dark:ring-slate-700">
                      <Loader2 className="size-3.5 animate-spin" aria-hidden />
                    </div>
                    <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-2.5 text-sm text-neutral-500 shadow-sm dark:border-slate-700/50 dark:bg-[#141c2b] dark:text-slate-400">
                      <span className="flex gap-1">
                        <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:0ms]" />
                        <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:150ms]" />
                        <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:300ms]" />
                      </span>
                      선장이 답변 중…
                    </div>
                  </div>
                )}
              </div>

              {/* 오류 */}
              {chat.error && (
                <p className="border-t border-rose-200 bg-rose-50 px-5 py-2.5 text-xs text-rose-700 dark:border-rose-900/30 dark:bg-rose-950/20 dark:text-rose-400">
                  {chat.error}
                </p>
              )}

              {/* 입력 영역 */}
              <form
                onSubmit={handleSubmit}
                className="border-t border-neutral-200 bg-white p-3 dark:border-[#252b3b] dark:bg-[#161a24]"
              >
                <label className="sr-only" htmlFor="smith-chat-input">
                  선장님께 질문하기
                </label>
                <div className="flex items-end gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 focus-within:border-slate-300 focus-within:ring-1 focus-within:ring-slate-200 dark:border-[#252b3b] dark:bg-[#1a1f2d] dark:focus-within:border-[#2d3447]">
                  <textarea
                    ref={inputRef}
                    id="smith-chat-input"
                    name="message"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onCompositionStart={() => {
                      isComposingRef.current = true
                    }}
                    onCompositionEnd={() => {
                      isComposingRef.current = false
                    }}
                    onKeyDown={onKeyDown}
                    rows={2}
                    placeholder="선장님께 질문하세요… (Enter 전송 / Shift+Enter 줄바꿈)"
                    disabled={chat.loading}
                    className="min-h-[2.75rem] flex-1 resize-none border-0 bg-transparent px-1 py-1 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none disabled:opacity-50 dark:text-neutral-100 dark:placeholder:text-neutral-600"
                  />
                  <Button
                    type="submit"
                    size="icon"
                    disabled={chat.loading || !draft.trim()}
                    aria-label="전송"
                    className="mb-0.5 size-9 shrink-0 rounded-lg bg-slate-700 text-amber-300 hover:bg-slate-600 disabled:opacity-40 dark:bg-[#0f1e35] dark:hover:bg-[#162035]"
                  >
                    {chat.loading ? (
                      <Loader2 className="size-4 animate-spin" aria-hidden />
                    ) : (
                      <CornerDownLeft className="size-4" aria-hidden />
                    )}
                  </Button>
                </div>
              </form>
            </div>

            {/* 우측 사이드바 */}
            <aside className="space-y-4">
              <div className="overflow-hidden rounded-xl border border-neutral-200 bg-neutral-50 dark:border-[#252b3b] dark:bg-[#1a1f2d]">
                <div className="border-b border-neutral-200 px-4 py-3 dark:border-[#252b3b]">
                  <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                    수업 안내
                  </p>
                </div>
                <div className="space-y-4 p-4 text-center text-neutral-700 dark:text-neutral-300">
                  <div>
                    <Ship className="mx-auto size-8 text-sky-500" />
                    <p className="mt-2 text-sm font-semibold">RMS Titanic</p>
                    <p className="text-xs text-neutral-500">White Star Line</p>
                  </div>
                  <div>
                    <MessageCircle className="mx-auto size-7 text-violet-500" />
                    <p className="mt-1 text-sm">역할 기반 대화</p>
                    <p className="text-xs text-neutral-500">선장 시점 Q&amp;A</p>
                  </div>
                  <div>
                    <Bot className="mx-auto size-7 text-rose-500" />
                    <p className="mt-1 text-sm">Gemini AI</p>
                    <p className="text-xs text-neutral-500">gemini-flash-lite</p>
                  </div>
                </div>
              </div>

              <article className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-sm leading-6 text-neutral-600 dark:border-[#252b3b] dark:bg-[#1a1f2d] dark:text-neutral-400">
                <p className="font-semibold text-neutral-900 dark:text-neutral-100">학습 포인트</p>
                <ul className="mt-2 space-y-1.5 text-xs leading-5">
                  <li>· LLM 프롬프트로 역할(페르소나) 지정</li>
                  <li>· 대화 이력을 컨텍스트로 전달</li>
                  <li>· 백엔드 Gemini API 연동 실습</li>
                </ul>
              </article>
            </aside>
          </div>
        </section>
      </main>
    </div>
  )
}
