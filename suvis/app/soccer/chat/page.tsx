"use client"

import Link from "next/link"
import { useCallback, useEffect, useRef, useState } from "react"
import { Bot, CornerDownLeft, Loader2, MessageCircle, Trophy } from "lucide-react"
import { Button } from "@/components/ui/button"
import { patchState } from "@/lib/form-status"
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

const SYSTEM_PROMPT = `당신은 K리그(한국 프로축구)를 오랫동안 취재해온 베테랑 해설위원입니다.
경기장·팀·선수·일정 등 K리그 전반에 대한 질문에 친근하고 열정적인 해설 톤으로 답해주세요.
확실하지 않은 최신 정보는 추측하지 말고 모른다고 솔직히 답하세요.
한국어로 대화합니다.`

const INITIAL_MESSAGE: ChatMessage = {
  role: "assistant",
  content: "안녕하세요! K리그 해설위원입니다. 경기장, 팀, 선수 등 축구에 대해 무엇이든 물어보세요.",
}

const initialChat: ChatState = {
  messages: [INITIAL_MESSAGE],
  loading: false,
  error: null,
}

export default function SoccerChatPage() {
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
      const res = await fetch(`/api/v1/contents/soccer/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
            content: data.reply?.trim() || "죄송해요, 다시 질문해주세요.",
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
              className="block rounded-md bg-neutral-100 px-3 py-2 text-sm font-semibold text-neutral-900 transition-colors hover:bg-neutral-200 dark:bg-[#252b3b] dark:text-neutral-100 dark:hover:bg-[#2d3447]"
            >
              채팅
            </Link>
          </div>
        </aside>

        {/* 메인 콘텐츠 */}
        <section className="rounded-xl border border-neutral-200 bg-white p-6 md:p-8 dark:border-[#252b3b] dark:bg-[#161a24]">
          <p className="text-xs font-semibold tracking-[0.2em] text-neutral-500">SOCCER</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
            K리그 해설위원과 대화
          </h1>
          <p className="mt-5 max-w-4xl text-sm leading-7 text-neutral-600 md:text-base dark:text-neutral-400">
            경기장·팀·선수·일정 등 K리그에 대해 자유롭게 질문하세요. Gemini AI가 해설위원 역할로
            답변합니다.
          </p>

          <div className="mt-8 grid gap-4 lg:grid-cols-[1fr_240px]">
            {/* 채팅 카드 */}
            <div className="overflow-hidden rounded-xl border border-neutral-200 dark:border-[#252b3b]">
              {/* 헤더 */}
              <div className="relative overflow-hidden bg-gradient-to-br from-emerald-700 via-emerald-800 to-emerald-900 px-6 py-5 dark:from-[#062616] dark:via-[#0a3320] dark:to-[#061f13]">
                {/* 잔디 라인 패턴 */}
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0 opacity-[0.07]"
                  style={{
                    backgroundImage:
                      "repeating-linear-gradient(90deg, transparent, transparent 18px, rgba(255,255,255,0.6) 18px, rgba(255,255,255,0.6) 19px)",
                  }}
                />
                <div
                  aria-hidden
                  className="pointer-events-none absolute top-1/2 right-6 -translate-y-1/2 opacity-[0.06]"
                >
                  <Trophy className="size-24 text-white" />
                </div>

                <div className="relative flex items-center gap-4">
                  <div className="flex size-14 shrink-0 items-center justify-center rounded-full bg-white/10 ring-2 ring-white/20 backdrop-blur-sm">
                    <Trophy className="size-7 text-amber-300" aria-hidden />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[10px] font-semibold tracking-[0.2em] text-amber-300/80 uppercase">
                      K League · 해설위원
                    </p>
                    <h2 className="mt-0.5 text-lg font-bold text-white">축구 해설위원</h2>
                    <p className="text-sm text-emerald-100">경기장·팀·선수·일정 Q&amp;A</p>
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
                          : "bg-emerald-800 text-amber-300 ring-emerald-700 dark:bg-[#0a3320] dark:text-amber-300 dark:ring-emerald-800"
                      )}
                      aria-hidden
                    >
                      {msg.role === "user" ? "나" : <Trophy className="size-3.5" />}
                    </div>

                    {/* 말풍선 */}
                    <div
                      className={cn(
                        "max-w-[82%] rounded-2xl px-4 py-2.5 text-[13px] leading-relaxed shadow-sm md:text-sm",
                        msg.role === "user"
                          ? "rounded-tr-sm border border-amber-200/60 bg-amber-50 text-neutral-900 dark:border-amber-900/30 dark:bg-amber-950/20 dark:text-neutral-100"
                          : "rounded-tl-sm border border-emerald-200 bg-white text-emerald-900 dark:border-emerald-800/50 dark:bg-[#0f1c14] dark:text-emerald-100"
                      )}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}

                {chat.loading && (
                  <div className="flex gap-2.5">
                    <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-emerald-800 text-amber-300 ring-1 ring-emerald-700 dark:bg-[#0a3320] dark:ring-emerald-800">
                      <Loader2 className="size-3.5 animate-spin" aria-hidden />
                    </div>
                    <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-emerald-200 bg-white px-4 py-2.5 text-sm text-neutral-500 shadow-sm dark:border-emerald-800/50 dark:bg-[#0f1c14] dark:text-emerald-300">
                      <span className="flex gap-1">
                        <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-emerald-400 [animation-delay:0ms]" />
                        <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-emerald-400 [animation-delay:150ms]" />
                        <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-emerald-400 [animation-delay:300ms]" />
                      </span>
                      해설위원이 답변 중…
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
                <label className="sr-only" htmlFor="soccer-chat-input">
                  해설위원께 질문하기
                </label>
                <div className="flex items-end gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 focus-within:border-emerald-300 focus-within:ring-1 focus-within:ring-emerald-200 dark:border-[#252b3b] dark:bg-[#1a1f2d] dark:focus-within:border-[#2d3447]">
                  <textarea
                    ref={inputRef}
                    id="soccer-chat-input"
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
                    placeholder="K리그에 대해 질문하세요… (Enter 전송 / Shift+Enter 줄바꿈)"
                    disabled={chat.loading}
                    className="min-h-[2.75rem] flex-1 resize-none border-0 bg-transparent px-1 py-1 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none disabled:opacity-50 dark:text-neutral-100 dark:placeholder:text-neutral-600"
                  />
                  <Button
                    type="submit"
                    size="icon"
                    disabled={chat.loading || !draft.trim()}
                    aria-label="전송"
                    className="mb-0.5 size-9 shrink-0 rounded-lg bg-emerald-800 text-amber-300 hover:bg-emerald-700 disabled:opacity-40 dark:bg-[#0a3320] dark:hover:bg-[#0d3d26]"
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
                    <Trophy className="mx-auto size-8 text-emerald-500" />
                    <p className="mt-2 text-sm font-semibold">K League</p>
                    <p className="text-xs text-neutral-500">한국 프로축구</p>
                  </div>
                  <div>
                    <MessageCircle className="mx-auto size-7 text-violet-500" />
                    <p className="mt-1 text-sm">역할 기반 대화</p>
                    <p className="text-xs text-neutral-500">해설위원 시점 Q&amp;A</p>
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
                  <li>· 프론트 → Gemini API 직접 연동 실습</li>
                </ul>
              </article>
            </aside>
          </div>
        </section>
      </main>
    </div>
  )
}
