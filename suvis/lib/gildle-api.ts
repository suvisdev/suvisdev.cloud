import { authHeader } from "@/lib/suvis-session"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

/** gildle 백엔드 클라이언트 — 앱(Flutter)과 같은 엔드포인트만 쓴다(2026-09-28 웹·앱 동일화).
 *  경로·루프는 비로그인 허용, 산책 기록은 세션 Bearer 필요. */

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) || "http://127.0.0.1:8000"

type ApiErrorBody = { detail?: unknown }

export type SeasonMode = "spring_autumn" | "summer_shade" | "winter_safety"

export type LoopCandidate = {
  path: string[]
  coordinates: [number, number][]
  length_m: number
  overlap_ratio: number
  bearing_deg: number
  shade_ratio: number | null
}

export type LoopResult = { candidates: LoopCandidate[]; night: boolean }

export type WalkCreateBody = {
  started_at: string
  ended_at: string
  distance_m: number
  duration_s: number
  path: [number, number][]
  season_mode: string
  avg_shade_score?: number
}

export type WalkSummary = {
  id: number
  started_at: string
  ended_at: string
  distance_m: number
  duration_s: number
  season_mode: string
  avg_shade_score: number | null
}

export type WalkDetail = WalkSummary & {
  path?: [number, number][]
  memo?: string | null
}

export type WalkStats = { total_count: number; total_distance_m: number; total_duration_s: number }

async function gildleFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api/gildle${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeader(),
      ...(init?.headers ?? {}),
    },
  })
  const data = (await res.json()) as T & ApiErrorBody
  if (!res.ok) {
    throw new Error(safeApiErrorMessage(data.detail, "요청을 처리하지 못했습니다.", res.status))
  }
  return data
}

export function findLoops(body: {
  lat: number
  lng: number
  target_m: number
  mode: SeasonMode
  limit?: number
}): Promise<LoopResult> {
  return gildleFetch<LoopResult>("/loops", {
    method: "POST",
    body: JSON.stringify({ limit: 3, ...body }),
  })
}

export function createWalk(body: WalkCreateBody): Promise<WalkDetail> {
  return gildleFetch<WalkDetail>("/walks", { method: "POST", body: JSON.stringify(body) })
}

export function listWalks(limit = 20, offset = 0): Promise<WalkSummary[]> {
  return gildleFetch<WalkSummary[]>(`/walks?limit=${limit}&offset=${offset}`)
}

export function getWalk(id: number): Promise<WalkDetail> {
  return gildleFetch<WalkDetail>(`/walks/${id}`)
}

export function walkStats(): Promise<WalkStats> {
  return gildleFetch<WalkStats>("/walks/stats")
}

export type PetPlaceItem = {
  id: string
  name: string
  category: string
  lat: number
  lng: number
  address: string
  url: string
  phone: string
}

export type RouteOptionKind = "fast" | "shade" | "green" | "via"

/** 경로 후보 — 빠른·그늘·푸른 길과 고를 이유, 경로 곁 반려동물 장소(2026-09-28). */
export type RouteOption = {
  kind: RouteOptionKind
  label: string
  reason: string
  highlights: string[]
  recommended: boolean
  path: string[]
  coordinates: [number, number][]
  length_m: number
  minutes: number
  extra_m: number
  shade_ratio: number | null
  green_ratio: number
  places: PetPlaceItem[]
}

type RouteOptionsBody = {
  start_lat: number
  start_lng: number
  end_lat: number
  end_lng: number
  mode: SeasonMode
  departure_time?: string
}

export function getRouteOptions(
  body: RouteOptionsBody
): Promise<{ options: RouteOption[]; night: boolean }> {
  return gildleFetch("/routes/options", { method: "POST", body: JSON.stringify(body) })
}

export function getRouteVia(
  body: RouteOptionsBody & {
    via_lat: number
    via_lng: number
    via_name: string
    base_kind: "fast" | "shade" | "green"
  }
): Promise<{ option: RouteOption }> {
  return gildleFetch("/routes/via", { method: "POST", body: JSON.stringify(body) })
}
