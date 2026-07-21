"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { Clapperboard, Loader2, Send, Sparkles } from "lucide-react"
import { patchState } from "@/lib/form-status"
import {
  MovaRecommendationCards,
  type MovaRecommendation,
} from "@/components/mova/mova-recommendation-cards"
import { coercePosterUrl } from "@/lib/mova-poster"
import { cn } from "@/lib/utils"
import { getSuvisSession } from "@/lib/suvis-session"
import { getDailyMovaChatSuggestions } from "@/lib/mova-chat-suggestions"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

type ChatMessage = {
  role: "user" | "assistant"
  content: string
  intentLabel?: string
  recommendations?: MovaRecommendation[]
}

type ChatState = {
  messages: ChatMessage[]
  loading: boolean
  error: string | null
}

type MessageFormProps = { message: string }
const CHAT_STORAGE_KEY = "mova-ai-chat-history-v1"

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    role: "assistant",
    content:
      "안녕하세요! Mova AI예요. 장르·분위기·OTT를 말씀해 주시면 짧은 소개와 함께 영화 3편을 추천해 드릴게요.",
  },
]

function normalizeRecommendation(raw: unknown): MovaRecommendation | null {
  if (!raw || typeof raw !== "object") return null
  const o = raw as Record<string, unknown>
  const title = typeof o.title === "string" ? o.title.trim() : ""
  if (!title) return null
  const id =
    typeof o.id === "string" && o.id.trim()
      ? o.id.trim()
      : title.toLowerCase().replace(/\s+/g, "-").slice(0, 64) || "movie"
  return {
    id,
    movieDbId: typeof o.movie_id === "number" ? o.movie_id : null,
    title,
    year: typeof o.year === "string" ? o.year : "",
    poster: coercePosterUrl(o.poster) ?? "",
    synopsis: typeof o.synopsis === "string" ? o.synopsis : "",
    platform:
      typeof o.platform === "string" && o.platform.trim() ? o.platform : null,
    hook:
      typeof o.hook === "string" && o.hook.trim()
        ? o.hook
        : "취향에 맞는 작품이에요.",
  }
}

function parseError(body: unknown, status: number): string {
  const detail =
    typeof body === "object" && body && "detail" in body
      ? (body as { detail: unknown }).detail
      : undefined
  return safeApiErrorMessage(detail, `요청에 실패했습니다. (${status})`, status)
}

/** Gemini JSON이 reply에 그대로 올 때 intro·picks 분리 */
function parseJsonReply(raw: string): { intro: string; picks: MovaRecommendation[] } {
  let text = raw.trim()
  if (!text) return { intro: "", picks: [] }
  if (text.startsWith("```")) {
    text = text.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "").trim()
  }
  if (!text.startsWith("{")) return { intro: text, picks: [] }

  try {
    const data = JSON.parse(text) as Record<string, unknown>
    const intro = typeof data.intro === "string" ? data.intro.trim() : ""
    const picks = Array.isArray(data.picks)
      ? data.picks
          .map(normalizeRecommendation)
          .filter((r): r is MovaRecommendation => r !== null)
      : []
    if (intro || picks.length) {
      return {
        intro:
          intro ||
          (picks.length ? "요청하신 취향에 맞춰 아래 작품을 골라봤어요." : text),
        picks,
      }
    }
  } catch {
    const introMatch = text.match(/"intro"\s*:\s*"((?:[^"\\]|\\.)*)"/)
    if (introMatch?.[1]) {
      return {
        intro: introMatch[1].replace(/\\n/g, "\n").replace(/\\"/g, '"'),
        picks: [],
      }
    }
  }

  return {
    intro: "추천을 정리했어요. 아래 작품을 확인해 주세요.",
    picks: [],
  }
}

function normalizeAssistantReply(
  reply: string,
  recommendations: MovaRecommendation[],
): { content: string; recommendations: MovaRecommendation[] } {
  const parsed = parseJsonReply(reply)
  const looksLikeJson = reply.trim().startsWith("{") || reply.trim().startsWith("```")
  const content =
    looksLikeJson && parsed.intro && !parsed.intro.trim().startsWith("{")
      ? parsed.intro
      : looksLikeJson
        ? parsed.intro
        : reply.trim() || parsed.intro

  const merged =
    recommendations.length > 0
      ? recommendations
      : parsed.picks.length > 0
        ? parsed.picks
        : recommendations

  return { content, recommendations: merged }
}

type MovaAiChatBarProps = {
  /** 랜딩(`/mova`) 하단 고정용 — 높이 축소 */
  compact?: boolean
  className?: string
}

export function MovaAiChatBar({ compact = false, className }: MovaAiChatBarProps = {}) {
  const [chat, setChat] = useState<ChatState>({
    messages: INITIAL_MESSAGES,
    loading: false,
    error: null,
  })
  const patchChat = (patch: Partial<ChatState>) => patchState(setChat, patch)

  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const autoSentRef = useRef(false)
  const hydratedRef = useRef(false)
  const dailySuggestions = useMemo(() => getDailyMovaChatSuggestions(3), [])
  const showSuggestions = !chat.messages.some((m) => m.role === "user")

  useEffect(() => {
    if (typeof window === "undefined") return
    try {
      const hasQ = new URLSearchParams(window.location.search).get("q")
      if (hasQ) {
        hydratedRef.current = true
        return
      }
      const raw = window.sessionStorage.getItem(CHAT_STORAGE_KEY)
      if (!raw) {
        hydratedRef.current = true
        return
      }
      const parsed = JSON.parse(raw) as Partial<ChatState>
      const messages = Array.isArray(parsed.messages) ? parsed.messages : []
      if (messages.length > 0) {
        setChat((prev) => ({ ...prev, messages }))
        autoSentRef.current = true
      }
    } catch {
      // ignore corrupted storage
    } finally {
      hydratedRef.current = true
    }
  }, [])

  useEffect(() => {
    if (typeof window === "undefined" || !hydratedRef.current) return
    try {
      window.sessionStorage.setItem(
        CHAT_STORAGE_KEY,
        JSON.stringify({ messages: chat.messages }),
      )
    } catch {
      // ignore quota/storage errors
    }
  }, [chat.messages])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" })
  }, [chat.messages, chat.loading])

  const sendMessage = useCallback(
    async (text: string): Promise<boolean> => {
      const trimmed = text.trim()
      if (!trimmed || chat.loading) return false

      patchChat({ error: null })
      const history = chat.messages.filter((m) => m.role === "user" || m.role === "assistant")
      const userMsg: ChatMessage = { role: "user", content: trimmed }
      setChat((prev) => ({
        ...prev,
        messages: [...prev.messages, userMsg],
        loading: true,
      }))

      try {
        const res = await fetch("/api/mova/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: trimmed,
            history: history.slice(-10).map((m) => ({ role: m.role, content: m.content })),
            model: "flash15",
            user_id: getSuvisSession()?.id ?? undefined,
          }),
        })
        const data = (await res.json()) as {
          reply?: string
          refined_query?: string
          recommendations?: MovaRecommendation[]
          detail?: unknown
        }
        if (!res.ok) throw new Error(parseError(data, res.status))
        const replyRaw = typeof data.reply === "string" ? data.reply.trim() : ""
        const refined =
          typeof data.refined_query === "string" ? data.refined_query.trim() : ""
        const apiRecs = Array.isArray(data.recommendations)
          ? data.recommendations
              .slice(0, 3)
              .map(normalizeRecommendation)
              .filter((r): r is MovaRecommendation => r !== null)
          : []
        const { content, recommendations } = normalizeAssistantReply(replyRaw, apiRecs)

        setChat((prev) => {
          const messages = [...prev.messages]
          const lastIdx = messages.length - 1
          if (refined && lastIdx >= 0 && messages[lastIdx]?.role === "user") {
            messages[lastIdx] = { ...messages[lastIdx], intentLabel: refined }
          }
          messages.push({
            role: "assistant",
            content: content || "추천을 준비하지 못했어요. 다시 질문해 주세요.",
            recommendations,
          })
          return { ...prev, messages, loading: false }
        })
        return true
      } catch (e) {
        const msg = e instanceof Error ? e.message : "알 수 없는 오류입니다."
        setChat((prev) => ({
          ...prev,
          error: msg,
          messages: prev.messages.slice(0, -1),
          loading: false,
        }))
        if (inputRef.current) inputRef.current.value = trimmed
        return false
      } finally {
        inputRef.current?.focus()
      }
    },
    [chat.loading, chat.messages],
  )

  useEffect(() => {
    if (!hydratedRef.current) return
    if (autoSentRef.current) return
    const raw = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("q") : null
    const initial = (raw || "").trim()
    if (!initial) return
    if (inputRef.current) inputRef.current.value = initial
    autoSentRef.current = true
    void sendMessage(initial)
  }, [sendMessage])

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = e.currentTarget
    const formData = new FormData(form)
    const formProps = Object.fromEntries(formData.entries()) as MessageFormProps
    const ok = await sendMessage(formProps.message)
    if (ok) form.reset()
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== "Enter" || e.shiftKey || e.nativeEvent.isComposing) return
    e.preventDefault()
    e.currentTarget.form?.requestSubmit()
  }

  return (
    <section
      className={cn(
        "relative flex w-full min-w-0 max-w-full flex-col overflow-hidden rounded-xl border border-[var(--mova-border)] bg-[var(--mova-surface)] shadow-[0_2px_12px_rgba(0,0,0,0.07)] dark:shadow-[0_12px_48px_rgba(0,0,0,0.45)]",
        compact
          ? "min-h-[min(360px,42vh)] max-h-[min(480px,52vh)]"
          : "min-h-[min(420px,65vh)] sm:min-h-[480px] lg:min-h-[640px]",
        className,
      )}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--mova-accent-soft)_0%,_transparent_55%),radial-gradient(ellipse_at_bottom_right,_rgba(139,127,212,0.08)_0%,_transparent_50%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 hidden opacity-[0.03] dark:block"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.15) 2px, rgba(255,255,255,0.15) 4px)",
        }}
      />

      <header className="relative z-10 flex items-center gap-3 border-b border-[var(--mova-border)] bg-[var(--mova-surface)]/90 px-4 py-3 backdrop-blur-md">
        <span className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-[var(--mova-accent)] to-[#6b2d4a] shadow-lg shadow-[var(--mova-accent-soft)]">
          <Clapperboard className="h-5 w-5 text-white" />
          <span className="absolute -right-0.5 -bottom-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-[var(--mova-bg)] ring-2 ring-[var(--mova-surface)]">
            <Sparkles className="h-2.5 w-2.5 text-[var(--mova-accent-bright)]" />
          </span>
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold tracking-wide text-[var(--mova-text)]">Mova AI 컨시어지</h2>
          <p className="text-[11px] text-neutral-500">맞춤 영화 · 드라마 추천</p>
        </div>
        <span className="hidden rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400 sm:inline">
          LIVE
        </span>
      </header>

      <div
        ref={listRef}
        className="relative z-10 flex-1 space-y-3 overflow-x-hidden overflow-y-auto px-3 py-4 md:px-4"
      >
        {chat.messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              "flex w-full min-w-0 gap-2.5",
              msg.role === "user" ? "flex-row-reverse" : "flex-row",
            )}
          >
            {msg.role === "assistant" && (
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--mova-border)] bg-[var(--mova-surface-2)]">
                <Sparkles className="h-3.5 w-3.5 text-[var(--mova-accent)]" />
              </span>
            )}
            <div
              className={cn(
                "flex min-w-0 flex-col gap-1",
                msg.role === "user"
                  ? "max-w-[min(85%,100%)] items-end"
                  : "max-w-[calc(100%-2.75rem)] flex-1 sm:max-w-[calc(100%-3rem)]",
              )}
            >
              <div
                className={cn(
                  "max-w-full rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed break-words [overflow-wrap:anywhere]",
                  msg.role === "user"
                    ? "rounded-tr-md bg-gradient-to-br from-[var(--mova-accent)] to-[#b84a72] text-white shadow-md shadow-[var(--mova-accent-soft)]"
                    : "rounded-tl-md border border-[var(--mova-border)] bg-[var(--mova-surface-2)] text-[var(--mova-text)]",
                )}
              >
                {msg.content}
              </div>
              {msg.role === "assistant" && msg.recommendations && msg.recommendations.length > 0 && (
                <div className="w-full min-w-0 max-w-full overflow-hidden">
                  <MovaRecommendationCards items={msg.recommendations} />
                </div>
              )}
              {msg.role === "user" && msg.intentLabel && (
                <p className="max-w-full px-1 text-right text-[10px] break-words text-neutral-500 [overflow-wrap:anywhere]">
                  DB 저장 · <span className="text-[var(--mova-accent-bright)]">{msg.intentLabel}</span>
                </p>
              )}
            </div>
          </div>
        ))}
        {chat.loading && (
          <div className="flex gap-2.5">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--mova-border)] bg-[var(--mova-surface-2)]">
              <Sparkles className="h-3.5 w-3.5 animate-pulse text-[var(--mova-accent)]" />
            </span>
            <div className="flex items-center gap-2 rounded-2xl rounded-tl-md border border-[var(--mova-border)] bg-[var(--mova-surface-2)] px-3.5 py-2.5 text-sm text-[var(--mova-muted)]">
              <Loader2 className="h-4 w-4 animate-spin text-[var(--mova-accent)]" />
              추천 큐레이션 중…
            </div>
          </div>
        )}
      </div>

      {chat.error && (
        <p className="relative z-10 border-t border-red-200 bg-red-50 px-4 py-2 text-xs text-red-600 dark:border-red-500/20 dark:bg-red-950/40 dark:text-red-300">
          {chat.error}
        </p>
      )}

      {showSuggestions && (
        <div className="relative z-10 flex max-w-full flex-wrap gap-2 border-t border-[var(--mova-border)] bg-[var(--mova-surface-2)] px-3 py-2.5 md:px-4">
          {dailySuggestions.map((s) => (
            <button
              key={s}
              type="button"
              disabled={chat.loading}
              onClick={() => void sendMessage(s)}
              className="rounded-full border border-[var(--mova-border)] bg-[var(--mova-surface)] px-3 py-1 text-xs text-[var(--mova-muted)] transition-colors hover:border-[var(--mova-accent)]/40 hover:bg-[var(--mova-accent-soft)] hover:text-[var(--mova-text)] disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <form
        onSubmit={(e) => void handleSubmit(e)}
        className="relative z-10 flex items-end gap-2 border-t border-[var(--mova-border)] bg-[var(--mova-bg)] px-3 py-3 md:px-4"
      >
        <textarea
          ref={inputRef}
          name="message"
          onKeyDown={onKeyDown}
          rows={1}
          placeholder="장르, 분위기, 배우를 알려주세요…"
          disabled={chat.loading}
          className="max-h-24 min-h-[44px] flex-1 resize-none rounded-lg border border-[var(--mova-border)] bg-[var(--mova-surface-2)] px-4 py-3 text-sm text-[var(--mova-text)] placeholder:text-neutral-500 outline-none transition-colors focus:border-[var(--mova-accent)]/50 focus:ring-1 focus:ring-[var(--mova-accent-soft)] disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={chat.loading}
          aria-label="전송"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[var(--mova-accent)] text-white shadow-lg shadow-[var(--mova-accent-soft)] transition-all hover:brightness-110 disabled:opacity-40 disabled:shadow-none"
        >
          {chat.loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
        </button>
      </form>

      {!compact && (
        <p className="relative z-10 border-t border-[var(--mova-border)] bg-[var(--mova-bg)] px-4 py-2 text-center text-[10px] text-neutral-500">
          AI 추천은 참고용입니다. 작품 상세는{" "}
          <Link
            href="/mova/main"
            className="text-neutral-400 underline-offset-2 hover:text-[var(--mova-accent-bright)] hover:underline"
          >
            메인 HOT 랭킹
          </Link>
          에서 확인하세요.
        </p>
      )}
    </section>
  )
}
