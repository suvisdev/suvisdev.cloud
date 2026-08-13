import { authHeader } from "@/lib/suvis-session"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://127.0.0.1:8000"

export type ChosungQuestion = {
  movie_id: number
  title: string
  chosung_condensed: string
  chosung_spaced: string
  is_korean: boolean
  cast_names: string[]
  poster_url: string
}

export type MemoryDeckPair = {
  movie_id: number
  title: string
  poster_url: string
}

export type MemoryDeck = {
  stage: number
  pairs: MemoryDeckPair[]
}

export type GameType = "chosung" | "memory"

export type LeaderboardEntry = {
  rank: number
  user_id: number
  nickname: string
  score: number
  hints_used: number
  played_at: string
  // memory 통합 리더보드용. chosung은 stage=null.
  // computed_score = 정렬 기준(memory: stage*1000+max(0,500-elapsed), chosung: score 그대로).
  stage: number | null
  computed_score: number
}

export type Leaderboard = {
  game_type: GameType
  stage: number | null
  top: LeaderboardEntry[]
  me: LeaderboardEntry | null
}

type ApiErrorBody = { detail?: unknown }

async function gamesFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/mova/games${path}`, {
    ...init,
    headers: {
      ...authHeader(),
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
  })
  const data = (await res.json()) as T & ApiErrorBody
  if (!res.ok) {
    throw new Error(
      safeApiErrorMessage(data.detail, "요청을 처리하지 못했습니다.", res.status),
    )
  }
  return data
}

export type ChosungCategory = "all" | "kr" | "foreign"

export function fetchNextChosungQuestion(
  category: ChosungCategory = "all",
): Promise<ChosungQuestion> {
  return gamesFetch<ChosungQuestion>(`/chosung/next?category=${category}`, {
    cache: "no-store",
  })
}

export function fetchMemoryDeck(stage: number): Promise<MemoryDeck> {
  return gamesFetch<MemoryDeck>(`/memory/deck?stage=${stage}`, { cache: "no-store" })
}

export function saveGameScore(payload: {
  game_type: GameType
  stage?: number
  score: number
  hints_used?: number
}): Promise<{ status: string }> {
  return gamesFetch<{ status: string }>("/scores", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function fetchLeaderboard(
  game: GameType,
  opts: { stage?: number; limit?: number } = {},
): Promise<Leaderboard> {
  const params = new URLSearchParams({ game })
  if (opts.stage !== undefined) params.set("stage", String(opts.stage))
  if (opts.limit !== undefined) params.set("limit", String(opts.limit))
  return gamesFetch<Leaderboard>(`/leaderboard?${params.toString()}`, { cache: "no-store" })
}

/** 클라이언트 정답 검증 — 공백·구두점·대소문자·한영 무시 후 비교. */
export function normalizeAnswer(s: string): string {
  return s
    .normalize("NFKC")
    .toLowerCase()
    .replace(/\s+/g, "")
    .replace(/[^0-9a-z가-힣ぁ-んァ-ヶ一-龥]/g, "")
}
