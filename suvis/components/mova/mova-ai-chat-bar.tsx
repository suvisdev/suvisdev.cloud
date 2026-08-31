"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { ArrowUp, Loader2, Sparkles } from "lucide-react"
import { patchState } from "@/lib/form-status"
import {
  MovaRecommendationCards,
  type MovaRecommendation,
} from "@/components/mova/mova-recommendation-cards"
import { coercePosterUrl } from "@/lib/mova-poster"
import { cn } from "@/lib/utils"
import { authHeader, clearSuvisSession, getSuvisSession } from "@/lib/suvis-session"
import { getConversation, type ConversationMessage } from "@/lib/mova-conversations-api"
import { getRotatingMovaChatSuggestions } from "@/lib/mova-chat-suggestions"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

type ChatEvaluation = {
  movie_id: number
  review_count: number
  avg_rating: number | null
  tmdb_rating: number | null
  excerpts: string[]
}

type ChatTheater = {
  name: string
  address: string
  distance_m: number | null
  place_url: string
  phone: string
}

type ChatBookingLink = { chain: string; url: string }

type ShowtimeSlot = {
  screen: string
  start_time: string
  end_time: string
  film_type: string
  seats_available: number
  seats_total: number
}

type CinemaShowtime = {
  cinema_name: string
  slots: ShowtimeSlot[]
}

type ChatBooking = {
  status: "showing" | "not_showing" | "need_region"
  region: string | null
  theaters: ChatTheater[]
  booking_links: ChatBookingLink[]
  showtimes: CinemaShowtime[]
}

type ChatMessage = {
  role: "user" | "assistant"
  content: string
  intentLabel?: string
  recommendations?: MovaRecommendation[]
  evaluation?: ChatEvaluation
  booking?: ChatBooking
}

type ChatState = {
  messages: ChatMessage[]
  loading: boolean
  error: string | null
}

const CHAT_STORAGE_KEY = "mova-ai-chat-history-v2"

type MovaAiChatBarProps = {
  /** 로그인 사용자 한정. null이면 새 대화(전송 시 서버가 생성). */
  conversationId?: number | null
  /** 서버 응답으로 conversation_id가 변한 뒤 호출(부모가 사이드바 갱신). */
  onConversationChanged?: (id: number | null) => void
}

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

function normalizeEvaluation(raw: unknown): ChatEvaluation | null {
  if (!raw || typeof raw !== "object") return null
  const o = raw as Record<string, unknown>
  if (typeof o.movie_id !== "number" || typeof o.review_count !== "number") return null
  return {
    movie_id: o.movie_id,
    review_count: o.review_count,
    avg_rating: typeof o.avg_rating === "number" ? o.avg_rating : null,
    tmdb_rating: typeof o.tmdb_rating === "number" ? o.tmdb_rating : null,
    excerpts: Array.isArray(o.excerpts)
      ? o.excerpts.filter((x): x is string => typeof x === "string")
      : [],
  }
}

function normalizeBooking(raw: unknown): ChatBooking | null {
  if (!raw || typeof raw !== "object") return null
  const o = raw as Record<string, unknown>
  if (o.status !== "showing" && o.status !== "not_showing" && o.status !== "need_region") {
    return null
  }
  const theaters: ChatTheater[] = Array.isArray(o.theaters)
    ? o.theaters.flatMap((t) => {
        if (!t || typeof t !== "object") return []
        const th = t as Record<string, unknown>
        if (typeof th.name !== "string" || !th.name) return []
        return [
          {
            name: th.name,
            address: typeof th.address === "string" ? th.address : "",
            distance_m: typeof th.distance_m === "number" ? th.distance_m : null,
            place_url: typeof th.place_url === "string" ? th.place_url : "",
            phone: typeof th.phone === "string" ? th.phone : "",
          },
        ]
      })
    : []
  const bookingLinks: ChatBookingLink[] = Array.isArray(o.booking_links)
    ? o.booking_links.flatMap((l) => {
        if (!l || typeof l !== "object") return []
        const link = l as Record<string, unknown>
        return typeof link.chain === "string" && typeof link.url === "string"
          ? [{ chain: link.chain, url: link.url }]
          : []
      })
    : []
  const showtimes: CinemaShowtime[] = Array.isArray(o.showtimes)
    ? o.showtimes.flatMap((cs) => {
        if (!cs || typeof cs !== "object") return []
        const c = cs as Record<string, unknown>
        if (typeof c.cinema_name !== "string") return []
        const slots: ShowtimeSlot[] = Array.isArray(c.slots)
          ? c.slots.flatMap((s) => {
              if (!s || typeof s !== "object") return []
              const sl = s as Record<string, unknown>
              return typeof sl.start_time === "string"
                ? [{
                    screen: typeof sl.screen === "string" ? sl.screen : "",
                    start_time: sl.start_time,
                    end_time: typeof sl.end_time === "string" ? sl.end_time : "",
                    film_type: typeof sl.film_type === "string" ? sl.film_type : "",
                    seats_available: typeof sl.seats_available === "number" ? sl.seats_available : 0,
                    seats_total: typeof sl.seats_total === "number" ? sl.seats_total : 0,
                  }]
                : []
            })
          : []
        return slots.length > 0 ? [{ cinema_name: c.cinema_name, slots }] : []
      })
    : []
  return {
    status: o.status,
    region: typeof o.region === "string" ? o.region : null,
    theaters,
    booking_links: bookingLinks,
    showtimes,
  }
}

function messagesFromConversation(msgs: ConversationMessage[]): ChatMessage[] {
  return msgs.map((m) => {
    const meta = m.meta ?? {}
    if (m.role === "user") {
      const refined = typeof meta.refined_query === "string" ? meta.refined_query : undefined
      return refined
        ? { role: "user", content: m.content, intentLabel: refined }
        : { role: "user", content: m.content }
    }
    const rawRecs = Array.isArray(meta.recommendations) ? meta.recommendations : []
    const recs: MovaRecommendation[] = []
    for (const raw of rawRecs) {
      const norm = normalizeRecommendation(raw)
      if (norm) recs.push(norm)
    }
    // 3트랙(2026-08-28): 평가·예매 payload도 meta에 저장돼 스레드 복원 시
    // 지표·영화관 패널이 재구성된다.
    const evaluation = normalizeEvaluation(meta.evaluation)
    const booking = normalizeBooking(meta.booking)
    return {
      role: "assistant",
      content: m.content,
      ...(recs.length > 0 ? { recommendations: recs } : {}),
      ...(evaluation ? { evaluation } : {}),
      ...(booking ? { booking } : {}),
    }
  })
}

export function MovaAiChatBar({
  conversationId: conversationIdProp,
  onConversationChanged,
}: MovaAiChatBarProps = {}) {
  const router = useRouter()
  const pathname = usePathname()
  const [chat, setChat] = useState<ChatState>({
    messages: [],
    loading: false,
    error: null,
  })
  const [inputValue, setInputValue] = useState("")
  const [conversationId, setConversationId] = useState<number | null>(
    conversationIdProp ?? null,
  )
  // URL ?q=X는 마운트 시점에 딱 한 번만 캡처. 이후엔 상태로만 흘려서 로드가
  // 끝난 뒤 기존 이력 뒤에 append하는 방식으로 send한다(기존 대화가 있어도
  // 키워드가 씹히지 않게 하기 위함).
  const [pendingQuery, setPendingQuery] = useState<string | null>(() => {
    if (typeof window === "undefined") return null
    const q = new URLSearchParams(window.location.search).get("q")
    return q?.trim() || null
  })
  const patchChat = (patch: Partial<ChatState>) => patchState(setChat, patch)

  const listRef = useRef<HTMLDivElement>(null)
  const heroInputRef = useRef<HTMLTextAreaElement>(null)
  const chatInputRef = useRef<HTMLTextAreaElement>(null)
  const autoSentRef = useRef(false)
  const chatRef = useRef(chat)
  chatRef.current = chat
  const conversationIdRef = useRef(conversationId)
  conversationIdRef.current = conversationId
  // 하이드레이션은 상태로 관리한다. ref로만 두면 hydration effect 실행 시
  // auto-send effect가 stale sendMessage(chat.messages=[])로 먼저 발화해
  // 히스토리가 빈 채로 서버에 요청이 나가는 race가 있다.
  const [hydrated, setHydrated] = useState(false)
  const dailySuggestions = useMemo(() => getRotatingMovaChatSuggestions(3), [])
  const isInitial = chat.messages.length === 0

  // 로딩 중 순환 문구 — Gemini 호출이 3~10초 걸릴 수 있어 정적 텍스트면 사용자가
  // 멈춘 것처럼 느낀다. 3초마다 문구를 갈아 끼워 "일하는 중" 느낌을 준다.
  const LOADING_HINTS = useMemo(
    () => [
      "요청하신 취향을 살펴보고 있어요…",
      "카탈로그에서 어울리는 작품을 찾는 중…",
      "AI가 최고의 조합을 골라보는 중…",
      "곧 추천해 드릴게요, 잠시만요…",
    ],
    [],
  )
  const [loadingHintIdx, setLoadingHintIdx] = useState(0)
  useEffect(() => {
    if (!chat.loading) return
    setLoadingHintIdx(0)
    const id = window.setInterval(() => {
      setLoadingHintIdx((i) => (i + 1) % LOADING_HINTS.length)
    }, 3000)
    return () => window.clearInterval(id)
  }, [chat.loading, LOADING_HINTS.length])

  // DB 모드(로그인 + 상위에서 prop 지정) vs sessionStorage 모드(비로그인)
  const dbMode = conversationIdProp !== undefined
  const dbModeRef = useRef(dbMode)
  dbModeRef.current = dbMode
  const onConversationChangedRef = useRef(onConversationChanged)
  onConversationChangedRef.current = onConversationChanged

  useEffect(() => {
    if (dbMode) {
      setHydrated(true)
      return
    }
    if (typeof window === "undefined") return
    // ?q=가 있어도 sessionStorage를 무조건 복원. ?q= 전송은 pendingQuery로 별도 처리.
    // 기존에는 ?q=가 있으면 복원을 스킵해서 이력이 있는 익명 사용자의 채팅이
    // 새 send로 덮여 사라지는 버그가 있었다.
    try {
      const raw = window.sessionStorage.getItem(CHAT_STORAGE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<ChatState>
        const messages = Array.isArray(parsed.messages) ? parsed.messages : []
        if (messages.length > 0) {
          setChat((prev) => ({ ...prev, messages }))
        }
      }
    } catch {
      // ignore corrupted storage
    } finally {
      setHydrated(true)
    }
  }, [dbMode])

  useEffect(() => {
    if (dbMode) return
    if (typeof window === "undefined" || !hydrated) return
    try {
      window.sessionStorage.setItem(
        CHAT_STORAGE_KEY,
        JSON.stringify({ messages: chat.messages }),
      )
    } catch {
      // ignore quota/storage errors
    }
  }, [chat.messages, dbMode, hydrated])

  // DB 모드: 상위에서 conversationIdProp이 바뀔 때(사이드바 클릭·새 대화 버튼)
  // 해당 대화를 서버에서 로드하거나 상태를 비운다.
  useEffect(() => {
    if (!dbMode) return
    setConversationId(conversationIdProp ?? null)
    if (conversationIdProp === null) {
      setChat({ messages: [], loading: false, error: null })
      setInputValue("")
      // URL ?q= 자동 전송은 계속 유효 — autoSentRef 건드리지 않는다.
      return
    }
    if (conversationIdProp === undefined) return
    // 로드가 끝난 뒤 auto-send effect가 fresh sendMessage(=업데이트된 chat.messages를
    // 클로저에 담은)로 재실행되면서 pendingQuery를 append로 전송한다.
    // 예전엔 여기서 autoSentRef를 즉시 잠가 ?q=가 씹혔다(2026-08-14 수정).
    let cancelled = false
    setChat((prev) => ({ ...prev, loading: true, error: null }))
    void getConversation(conversationIdProp)
      .then((detail) => {
        if (cancelled) return
        setChat({
          messages: messagesFromConversation(detail.messages),
          loading: false,
          error: null,
        })
      })
      .catch((e) => {
        if (cancelled) return
        setChat({
          messages: [],
          loading: false,
          error: e instanceof Error ? e.message : "대화를 불러오지 못했습니다.",
        })
      })
    return () => {
      cancelled = true
    }
  }, [conversationIdProp, dbMode])

  useEffect(() => {
    if (isInitial) return
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" })
  }, [chat.messages, chat.loading, isInitial])

  // 히어로 → 채팅 모드 전환 후 채팅 입력창에 자동 포커스
  useEffect(() => {
    if (isInitial || chat.loading) return
    chatInputRef.current?.focus({ preventScroll: true })
  }, [isInitial, chat.loading])

  const sendMessage = useCallback(
    async (text: string): Promise<boolean> => {
      const trimmed = text.trim()
      if (!trimmed || chatRef.current.loading) return false

      patchChat({ error: null })
      const history = chatRef.current.messages
      const userMsg: ChatMessage = { role: "user", content: trimmed }
      setChat((prev) => ({
        ...prev,
        messages: [...prev.messages, userMsg],
        loading: true,
      }))
      setInputValue("")

      const body = JSON.stringify({
        message: trimmed,
        history: history.slice(-10).map((m) => ({ role: m.role, content: m.content })),
        model: "flash15",
        conversation_id: conversationIdRef.current,
      })
      const doFetch = (withAuth: boolean) =>
        fetch("/api/mova/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(withAuth ? authHeader() : {}),
          },
          body,
        })

      try {
        let res = await doFetch(true)
        // 만료·손상된 JWT면 백엔드가 익명 강등 대신 401을 낸다(설계 의도).
        // 프론트에선 세션을 조용히 정리하고 익명으로 1회 재시도해 채팅 자체는
        // 끊기지 않게 한다.
        if (res.status === 401 && getSuvisSession()) {
          clearSuvisSession()
          res = await doFetch(false)
        }
        const data = (await res.json()) as {
          reply?: string
          refined_query?: string
          recommendations?: MovaRecommendation[]
          conversation_id?: number | null
          evaluation?: ChatEvaluation | null
          booking?: ChatBooking | null
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
            ...(data.evaluation ? { evaluation: data.evaluation } : {}),
            ...(data.booking ? { booking: data.booking } : {}),
          })
          return { ...prev, messages, loading: false }
        })
        if (dbModeRef.current) {
          const nextConvId = typeof data.conversation_id === "number" ? data.conversation_id : null
          setConversationId(nextConvId)
          onConversationChangedRef.current?.(nextConvId)
        }
        return true
      } catch (e) {
        const msg = e instanceof Error ? e.message : "알 수 없는 오류입니다."
        setChat((prev) => ({
          ...prev,
          error: msg,
          messages: prev.messages.slice(0, -1),
          loading: false,
        }))
        setInputValue(trimmed)
        return false
      }
    },
    [],
  )

  useEffect(() => {
    if (!hydrated) return
    if (autoSentRef.current) return
    if (!pendingQuery) return
    // 진행 중인 로드·send가 있으면 대기. DB 모드에서 conversation을 불러오는
    // 동안엔 chat.loading=true로 잠기며, 로드 완료 후 setChat이 커밋되면
    // sendMessage useCallback이 새 chat.messages를 담아 재생성되고 이 effect가
    // 다시 실행돼 append 전송이 이루어진다.
    if (chat.loading) return
    autoSentRef.current = true
    setPendingQuery(null)
    void sendMessage(pendingQuery).finally(() => {
      // 뒤로 가기로 재진입해도 auto-send가 다시 발화하지 않도록 URL에서 q 제거.
      router.replace(pathname, { scroll: false })
    })
  }, [hydrated, pendingQuery, chat.loading, sendMessage, router, pathname])

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    void sendMessage(inputValue)
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== "Enter" || e.shiftKey || e.nativeEvent.isComposing) return
    e.preventDefault()
    e.currentTarget.form?.requestSubmit()
  }

  const canSubmit = inputValue.trim().length > 0 && !chat.loading

  // ─── 히어로 모드 ──────────────────────────────────────────────────
  if (isInitial) {
    return (
      <section className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center px-4 py-8 md:px-6 md:py-12">
        <div className="mb-5 w-full text-center sm:mb-6">
          <p className="text-base font-medium text-mova-muted sm:text-lg">
            무엇이 궁금하세요?
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="relative w-full rounded-2xl border border-mova-border bg-mova-surface shadow-[0_8px_40px_rgba(0,0,0,0.08)] transition-shadow focus-within:border-mova-accent/40 focus-within:shadow-[0_8px_48px_rgba(190,24,93,0.15)] dark:shadow-[0_8px_40px_rgba(0,0,0,0.45)]"
        >
          <textarea
            ref={heroInputRef}
            name="message"
            rows={1}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={chat.loading}
            placeholder="장르, 분위기, 배우를 알려주세요…"
            className="max-h-32 min-h-[3.25rem] w-full resize-none bg-transparent px-4 py-3.5 pr-12 text-base leading-relaxed text-mova-text placeholder:text-neutral-500 outline-none disabled:opacity-60 sm:px-5 sm:py-4 sm:pr-14"
          />
          <button
            type="submit"
            disabled={!canSubmit}
            aria-label="AI 추천 받기"
            className={cn(
              "absolute right-3 bottom-3 flex h-9 w-9 items-center justify-center rounded-lg transition-all",
              canSubmit
                ? "bg-mova-accent text-white shadow-md hover:brightness-110"
                : "bg-mova-surface-2 text-mova-muted",
              "disabled:opacity-40",
            )}
          >
            {chat.loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowUp className="h-4 w-4" strokeWidth={2.5} />
            )}
          </button>
        </form>

        <div className="mt-3 flex flex-wrap items-center justify-center gap-1.5 px-1 sm:mt-4 sm:gap-2">
          {dailySuggestions.map((hint) => (
            <button
              key={hint}
              type="button"
              disabled={chat.loading}
              onClick={() => void sendMessage(hint)}
              className="rounded-full border border-mova-border bg-mova-surface px-3 py-1.5 text-xs text-mova-muted transition-colors hover:border-mova-accent/30 hover:bg-mova-accent-soft hover:text-mova-text disabled:opacity-50"
            >
              {hint}
            </button>
          ))}
        </div>

        {chat.error && (
          <p className="mt-4 text-xs text-red-500 dark:text-red-400">{chat.error}</p>
        )}
      </section>
    )
  }

  // ─── 채팅 모드 ────────────────────────────────────────────────────
  return (
    // min-h-0: flex-1 child의 기본 min-height:auto가 콘텐츠 높이를 요구해
    // 리스트의 overflow-y-auto가 안 걸리는 flexbox 관용적 함정 방지.
    <section className="mx-auto flex w-full min-h-0 max-w-3xl flex-1 flex-col px-4 md:px-6">
      <div
        ref={listRef}
        className="min-h-0 flex-1 space-y-4 overflow-y-auto py-3"
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
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-mova-border bg-mova-surface-2">
                <Sparkles className="h-3.5 w-3.5 text-mova-accent" />
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
                  "max-w-full rounded-2xl px-4 py-2.5 text-sm leading-relaxed break-words [overflow-wrap:anywhere]",
                  msg.role === "user"
                    ? "rounded-tr-md bg-gradient-to-br from-mova-accent to-[#b84a72] text-white shadow-md shadow-mova-accent-soft"
                    : "rounded-tl-md border border-mova-border bg-mova-surface-2 text-mova-text",
                )}
              >
                {msg.content}
              </div>
              {msg.role === "assistant" && msg.recommendations && msg.recommendations.length > 0 && (
                <div className="w-full min-w-0 max-w-full overflow-hidden">
                  <MovaRecommendationCards items={msg.recommendations} />
                </div>
              )}
              {msg.role === "assistant" && msg.evaluation && (
                <ChatEvaluationPanel evaluation={msg.evaluation} />
              )}
              {msg.role === "assistant" && msg.booking && msg.booking.status === "showing" && (
                <ChatBookingPanel booking={msg.booking} />
              )}
              {msg.role === "user" && msg.intentLabel && (
                <p className="max-w-full px-1 text-right text-[10px] break-words text-neutral-500 [overflow-wrap:anywhere]">
                  DB 저장 · <span className="text-mova-accent-bright">{msg.intentLabel}</span>
                </p>
              )}
            </div>
          </div>
        ))}
        {chat.loading && (
          <div className="flex gap-2.5">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-mova-border bg-mova-surface-2">
              <Sparkles className="h-3.5 w-3.5 animate-pulse text-mova-accent" />
            </span>
            <div className="flex flex-col gap-2">
              {/* 3D 클래퍼보드 감성 로딩 — 채팅 대기 시간(3~10초)이 브랜드 순간이
                  되도록 인라인 재생. muted+playsInline+loop로 자동 재생 정책 회피. */}
              {/* 원본 1280×720 하단 문구("Mova가 찾아줄게")가 폭 ~85%까지 차므로
                  크롭 없이 16:9 그대로 보여준다(예전 7:5 크롭은 문구를 잘랐다). */}
              <div className="aspect-video w-40 overflow-hidden rounded-2xl border border-mova-border bg-black shadow-sm md:w-48">
                <video
                  src="/mova-clapperboard-loading.mp4"
                  autoPlay
                  loop
                  muted
                  playsInline
                  preload="auto"
                  aria-hidden
                  className="h-full w-full object-cover"
                />
              </div>
              <div className="flex items-center gap-2 text-xs text-mova-muted">
                <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-mova-accent" />
                <span key={loadingHintIdx} className="animate-in fade-in duration-300">
                  {LOADING_HINTS[loadingHintIdx]}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {chat.error && (
        <p className="border-t border-red-200 bg-red-50 px-4 py-2 text-xs text-red-600 dark:border-red-500/20 dark:bg-red-950/40 dark:text-red-300">
          {chat.error}
        </p>
      )}

      <form
        onSubmit={handleSubmit}
        className="sticky bottom-0 z-10 border-t border-mova-border bg-mova-bg/95 py-2 backdrop-blur-md"
      >
        <div className="relative rounded-2xl border border-mova-border bg-mova-surface shadow-sm transition-shadow focus-within:border-mova-accent/40 focus-within:shadow-[0_4px_24px_rgba(190,24,93,0.12)]">
          <textarea
            ref={chatInputRef}
            name="message"
            rows={1}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={chat.loading}
            placeholder="장르, 분위기, 배우를 알려주세요…"
            className="max-h-32 min-h-[3rem] w-full resize-none bg-transparent px-4 py-3 pr-12 text-sm leading-relaxed text-mova-text placeholder:text-neutral-500 outline-none disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={!canSubmit}
            aria-label="전송"
            className={cn(
              "absolute right-2.5 bottom-2.5 flex h-8 w-8 items-center justify-center rounded-lg transition-all",
              canSubmit
                ? "bg-mova-accent text-white shadow-md hover:brightness-110"
                : "bg-mova-surface-2 text-mova-muted",
              "disabled:opacity-40",
            )}
          >
            {chat.loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowUp className="h-4 w-4" strokeWidth={2.5} />
            )}
          </button>
        </div>
      </form>
    </section>
  )
}

function ChatEvaluationPanel({ evaluation }: { evaluation: ChatEvaluation }) {
  const stats: string[] = [`mova 리뷰 ${evaluation.review_count}건`]
  if (evaluation.avg_rating !== null) stats.push(`자체 평균 ${evaluation.avg_rating}점`)
  if (evaluation.tmdb_rating !== null) stats.push(`TMDB ${evaluation.tmdb_rating}점`)
  return (
    <div className="w-full max-w-full rounded-2xl rounded-tl-md border border-mova-border bg-mova-surface-2 px-4 py-3">
      <div className="flex flex-wrap gap-1.5">
        {stats.map((s) => (
          <span
            key={s}
            className="rounded-full border border-mova-border bg-mova-bg px-2.5 py-0.5 text-[11px] text-mova-text"
          >
            {s}
          </span>
        ))}
      </div>
      {evaluation.excerpts.length > 0 && (
        <ul className="mt-2 space-y-1">
          {evaluation.excerpts.map((text) => (
            <li
              key={text}
              className="border-l-2 border-mova-accent pl-2 text-xs leading-relaxed text-neutral-400 break-words [overflow-wrap:anywhere]"
            >
              “{text}”
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function ChatBookingPanel({ booking }: { booking: ChatBooking }) {
  return (
    <div className="w-full max-w-full rounded-2xl rounded-tl-md border border-mova-border bg-mova-surface-2 px-4 py-3">
      {booking.theaters.length > 0 && (
        <ul className="space-y-1.5">
          {booking.theaters.map((t) => (
            <li key={`${t.name}-${t.address}`} className="text-xs leading-relaxed">
              <a
                href={t.place_url || undefined}
                target="_blank"
                rel="noreferrer"
                className="font-semibold text-mova-text hover:text-mova-accent-bright"
              >
                {t.name}
              </a>
              <span className="text-neutral-400">
                {" "}
                · {t.address}
                {t.distance_m !== null && ` · 약 ${t.distance_m}m`}
              </span>
            </li>
          ))}
        </ul>
      )}
      {booking.showtimes.length > 0 && (
        <div className={cn("space-y-2", booking.theaters.length > 0 && "mt-3")}>
          {booking.showtimes.map((cs) => (
            <div key={cs.cinema_name}>
              <p className="mb-1 text-[11px] font-semibold text-mova-accent">
                {cs.cinema_name} 시간표
              </p>
              <div className="flex flex-wrap gap-1.5">
                {cs.slots.map((s) => (
                  <span
                    key={`${s.screen}-${s.start_time}`}
                    className="inline-flex items-center gap-1 rounded-md border border-mova-border bg-mova-bg px-2 py-0.5 text-[11px] text-mova-text"
                  >
                    <span className="font-medium">{s.start_time}</span>
                    <span className="text-neutral-500">{s.screen}</span>
                    {s.film_type && s.film_type !== "2D" && (
                      <span className="text-mova-accent">{s.film_type}</span>
                    )}
                    {s.seats_total > 0 && (
                      <span className="text-neutral-500">
                        {s.seats_available}/{s.seats_total}석
                      </span>
                    )}
                  </span>
                ))}
              </div>
            </div>
          ))}
          <p className="text-[10px] text-neutral-500">롯데시네마 기준 · 실시간 좌석은 다를 수 있어요</p>
        </div>
      )}
      {booking.booking_links.length > 0 && (
        <div className={cn("flex flex-wrap gap-1.5", (booking.theaters.length > 0 || booking.showtimes.length > 0) && "mt-2.5")}>
          {booking.booking_links.map((link) => (
            <a
              key={link.chain}
              href={link.url}
              target="_blank"
              rel="noreferrer"
              className="rounded-full border border-mova-border bg-mova-bg px-3 py-1 text-[11px] text-mova-text transition-colors hover:border-mova-accent hover:text-mova-accent-bright"
            >
              {link.chain} 예매 검색
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
