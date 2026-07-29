"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { CornerDownLeft, MessageCircle, Mic, Plus, SlidersHorizontal, X } from "lucide-react"
import { patchState } from "@/lib/form-status"
import { cn } from "@/lib/utils"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

type Role = "user" | "assistant"
type ChatMessage = { role: Role; content: string }

type ChatUiState = {
  open: boolean
  listening: boolean
}

type ChatState = {
  messages: ChatMessage[]
  loading: boolean
  error: string | null
}

type MessageFormProps = { message: string }

// LESSON의 LangChain 채팅(app/langchain/chat/page.tsx)과 동일한 백엔드 —
// semantic_router가 의도를 판단한 뒤 LangChain 체인이 답변을 생성한다.
const CHAT_API = "/api/v1/langchain/chat"

type ChatApiResponse = { reply?: string }
type ChatApiErrorBody = { detail?: string | { msg?: string }[] }
type SpeechRecognitionAlternativeLike = { transcript: string }
type SpeechRecognitionResultLike = { 0: SpeechRecognitionAlternativeLike }
type SpeechRecognitionEventLike = {
  results: { 0: SpeechRecognitionResultLike }
}
type SpeechRecognitionInstanceLike = {
  lang: string
  interimResults: boolean
  maxAlternatives: number
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

const initialChat: ChatState = {
  messages: [],
  loading: false,
  error: null,
}

function parseChatApiError(body: ChatApiErrorBody, status: number): string {
  const raw =
    safeApiErrorMessage(body.detail, `요청에 실패했습니다. (${status})`, status) ||
    `요청에 실패했습니다. (${status})`

  if (status === 429 || raw.includes("429") || /quota|resource_exhausted|한도/i.test(raw)) {
    return "AI 사용 한도에 도달했습니다. 잠시 후 다시 시도해 주세요."
  }
  if (raw.length > 280) return `${raw.slice(0, 280)}…`
  return raw
}

export function SuvisChatPanel() {
  const [ui, setUi] = useState<ChatUiState>({ open: false, listening: false })
  const [chat, setChat] = useState<ChatState>(initialChat)
  const patchChat = (patch: Partial<ChatState>) => patchState(setChat, patch)
  const patchUi = (patch: Partial<ChatUiState>) => patchState(setUi, patch)

  const listEndRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const recognitionRef = useRef<SpeechRecognitionInstanceLike | null>(null)

  useEffect(() => {
    if (!ui.open) return
    listEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" })
  }, [chat.messages, chat.loading, ui.open])

  useEffect(() => {
    if (ui.open) {
      const t = window.setTimeout(() => inputRef.current?.focus(), 120)
      return () => window.clearTimeout(t)
    }
  }, [ui.open])

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || chat.loading) return

      patchChat({ error: null })
      const nextMessages: ChatMessage[] = [...chat.messages, { role: "user", content: trimmed }]
      patchChat({ messages: nextMessages, loading: true })

      try {
        const res = await fetch(CHAT_API, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages: nextMessages }),
        })
        const data = (await res.json()) as ChatApiResponse & ChatApiErrorBody
        if (!res.ok) {
          throw new Error(parseChatApiError(data, res.status))
        }
        const reply = data.reply?.trim() ?? ""
        setChat((prev) => ({
          ...prev,
          messages: [...prev.messages, { role: "assistant", content: reply || "(응답 없음)" }],
          loading: false,
        }))
      } catch (e) {
        const msg = e instanceof Error ? e.message : "알 수 없는 오류입니다."
        setChat((prev) => ({
          ...prev,
          error: msg,
          messages: prev.messages.slice(0, -1),
          loading: false,
        }))
        if (inputRef.current) inputRef.current.value = trimmed
      }
    },
    [chat.loading, chat.messages],
  )

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = e.currentTarget
    const formData = new FormData(form)
    const formProps = Object.fromEntries(formData.entries()) as MessageFormProps
    await sendMessage(formProps.message)
    form.reset()
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== "Enter" || e.shiftKey) return
    if (e.nativeEvent.isComposing) return
    e.preventDefault()
    e.currentTarget.form?.requestSubmit()
  }

  const toggleMic = () => {
    if (typeof window === "undefined") return

    if (ui.listening && recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        /* ignore */
      }
      recognitionRef.current = null
      patchUi({ listening: false })
      return
    }

    const win = window as Window & {
      SpeechRecognition?: { new (): SpeechRecognitionInstanceLike }
      webkitSpeechRecognition?: { new (): SpeechRecognitionInstanceLike }
    }
    const SR = win.SpeechRecognition ?? win.webkitSpeechRecognition
    if (!SR) {
      patchChat({ error: "이 브라우저에서는 음성 인식을 지원하지 않습니다." })
      return
    }

    const recognition = new SR()
    recognitionRef.current = recognition
    recognition.lang = "ko-KR"
    recognition.interimResults = false
    recognition.maxAlternatives = 1
    recognition.onresult = (event: SpeechRecognitionEventLike) => {
      const transcript = event.results[0]?.[0]?.transcript
      if (transcript && inputRef.current) {
        const el = inputRef.current
        el.value = el.value ? `${el.value} ${transcript}` : transcript
      }
      patchUi({ listening: false })
      recognitionRef.current = null
    }
    recognition.onerror = () => {
      patchUi({ listening: false })
      recognitionRef.current = null
      patchChat({ error: "음성 인식 중 오류가 발생했습니다." })
    }
    recognition.onend = () => {
      patchUi({ listening: false })
      recognitionRef.current = null
    }
    patchUi({ listening: true })
    patchChat({ error: null })
    recognition.start()
  }

  return (
    <>
      {ui.open && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-neutral-900/15 backdrop-blur-[1px]"
          aria-label="채팅 닫기"
          onClick={() => patchUi({ open: false })}
        />
      )}

      <div
        className={cn(
          "fixed right-4 z-50 w-[min(calc(100vw-2rem),24rem)] transition-all duration-200 ease-out",
          ui.open
            ? "bottom-[4.75rem] translate-y-0 opacity-100"
            : "pointer-events-none bottom-[4.75rem] translate-y-3 opacity-0",
        )}
        aria-hidden={!ui.open}
      >
        <div
          id="suvis-chat-panel"
          className="pointer-events-auto overflow-hidden rounded-2xl border border-neutral-300/80 bg-white shadow-lg shadow-neutral-900/10 md:rounded-3xl"
          role="dialog"
          aria-label="Suvis 채팅"
          aria-modal="true"
        >
          <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
            <div>
              <p className="text-sm font-bold tracking-tight text-neutral-900">
                Suvis<span className="font-extrabold">dev</span> AI
              </p>
              <p className="text-[11px] text-neutral-500">무엇이든 물어보세요</p>
            </div>
            <button
              type="button"
              onClick={() => patchUi({ open: false })}
              className="flex size-8 items-center justify-center rounded-full text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
              aria-label="닫기"
            >
              <X className="size-4" aria-hidden />
            </button>
          </div>

          {(chat.messages.length > 0 || chat.loading) && (
            <div
              ref={scrollRef}
              className="max-h-[min(36vh,280px)] overflow-y-auto overscroll-contain border-b border-neutral-200 bg-[#f5f5f5]/60 p-3"
              role="log"
              aria-live="polite"
            >
              <div className="flex min-h-full flex-col justify-end gap-2">
                {chat.messages.map((m, i) => (
                  <div
                    key={`${i}-${m.role}`}
                    className={cn(
                      "max-w-[92%] rounded-2xl px-3 py-2 text-xs leading-relaxed md:text-[13px]",
                      m.role === "user"
                        ? "ml-auto border border-[#e8d020]/50 bg-[#f0dc3a]/35 text-neutral-900"
                        : "mr-auto border border-neutral-200 bg-white text-neutral-700 shadow-sm",
                    )}
                  >
                    <span className="sr-only">{m.role === "user" ? "나" : "Suvis"}: </span>
                    {m.content}
                  </div>
                ))}
                {chat.loading && (
                  <div className="mr-auto max-w-[92%] rounded-2xl border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-500 shadow-sm">
                    답변 생성 중…
                  </div>
                )}
                <div ref={listEndRef} className="h-px shrink-0" aria-hidden />
              </div>
            </div>
          )}

          <form onSubmit={(e) => void handleSubmit(e)} className="p-3 md:p-4">
            <label className="sr-only" htmlFor="suvis-chat-input">
              Suvis에게 물어보기
            </label>
            <textarea
              ref={inputRef}
              id="suvis-chat-input"
              name="message"
              rows={2}
              onKeyDown={onKeyDown}
              placeholder="Suvis에게 물어보기"
              disabled={chat.loading}
              className="min-h-[2.5rem] w-full resize-none border-0 bg-transparent text-[13px] leading-snug text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-0 disabled:opacity-60"
            />

            <div className="mt-2 flex items-center justify-between gap-1.5 border-t border-neutral-200 pt-2.5">
              <div className="flex items-center gap-0.5">
                <button
                  type="button"
                  disabled
                  title="첨부는 곧 지원 예정"
                  className="flex size-7 items-center justify-center rounded-full text-neutral-300"
                  aria-disabled
                >
                  <Plus className="size-4" aria-hidden />
                </button>
                <button
                  type="button"
                  disabled
                  title="도구는 곧 지원 예정"
                  className="flex items-center gap-1 rounded-full px-1.5 py-1 text-[11px] text-neutral-300"
                  aria-disabled
                >
                  <SlidersHorizontal className="size-3.5 shrink-0" aria-hidden />
                  도구
                </button>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="submit"
                  disabled={chat.loading}
                  title="전송 (Enter)"
                  aria-label="전송"
                  className="flex size-8 items-center justify-center rounded-full bg-[#f0dc3a] text-neutral-900 transition-colors hover:bg-[#e8d020] disabled:pointer-events-none disabled:opacity-40"
                >
                  <CornerDownLeft className="size-4" aria-hidden />
                </button>

                <button
                  type="button"
                  onClick={toggleMic}
                  disabled={chat.loading}
                  title={ui.listening ? "음성 입력 중지" : "음성 입력"}
                  className={cn(
                    "flex size-8 items-center justify-center rounded-full text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900 disabled:opacity-50",
                    ui.listening && "bg-[#f0dc3a]/40 text-neutral-900 ring-1 ring-[#e8d020]",
                  )}
                >
                  <Mic className="size-4" aria-hidden />
                </button>
              </div>
            </div>

            {chat.error && (
              <p className="mt-2 text-xs text-red-600" role="alert">
                {chat.error}
              </p>
            )}
          </form>
        </div>
      </div>

      <button
        type="button"
        onClick={() => patchUi({ open: !ui.open })}
        className={cn(
          "fixed bottom-4 right-4 z-[60] flex size-14 items-center justify-center rounded-full border border-neutral-300/80 bg-neutral-200/90 text-neutral-800 shadow-md transition-all hover:scale-105 hover:bg-neutral-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400/50 active:scale-95",
          ui.open && "border-neutral-300 bg-white text-neutral-900 shadow-lg hover:bg-neutral-50",
        )}
        aria-label={ui.open ? "채팅 닫기" : "Suvis 채팅 열기"}
        aria-expanded={ui.open}
        aria-controls="suvis-chat-panel"
      >
        {ui.open ? (
          <X className="size-6" aria-hidden />
        ) : (
          <MessageCircle className="size-6" strokeWidth={1.75} aria-hidden />
        )}
      </button>
    </>
  )
}