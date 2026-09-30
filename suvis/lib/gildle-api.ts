import { safeApiErrorMessage } from "@/lib/user-facing-error"

/** gildle 백엔드 클라이언트 — 앱(Flutter)과 같은 엔드포인트만 쓴다(2026-09-28 웹·앱 동일화).
 *  경로·루프는 비로그인 허용, 산책 기록은 세션 Bearer 필요. */

type ApiErrorBody = { detail?: unknown }

export type SeasonMode = "spring_autumn" | "summer_shade" | "winter_safety"

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
  const res = await fetch(`/api/backend/api/gildle${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  })
  const data = (await res.json()) as T & ApiErrorBody
  if (!res.ok) {
    throw new Error(safeApiErrorMessage(data.detail, "요청을 처리하지 못했습니다.", res.status))
  }
  return data
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

export type RouteOptionKind = "fast" | "shade" | "green" | "flat" | "hilly" | "via"
export type WalkPreference = Exclude<RouteOptionKind, "via">

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
  climb_m: number | null
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
    base_kind: WalkPreference
  }
): Promise<{ option: RouteOption }> {
  return gildleFetch("/routes/via", { method: "POST", body: JSON.stringify(body) })
}

export type WalkStopCategory = "동물병원" | "펫샵" | "용품점" | "애견카페"

/** 시간·거리·선호로 산책 추천 — 자연어는 7.8B가 이해하고 규칙이 검증한다(2026-09-28). */
export type WalkPlanResult = {
  understood: {
    kind: "loop" | "route"
    minutes: number | null
    distance_km: number | null
    preference: WalkPreference
    stops: WalkStopCategory[]
    destination: WalkStopCategory | null
    source: "llm" | "rules" | "form"
  }
  /** 문장의 목적지 종류를 서버가 가장 가까운 실제 장소로 고른 결과(2026-09-29). */
  destination_place: {
    name: string
    category: WalkStopCategory
    lat: number
    lng: number
    address: string
  } | null
  /** route에서 들를 곳(stops)이 있으면 모든 후보가 거치는 장소(2026-09-29). */
  via_place: {
    name: string
    category: WalkStopCategory
    lat: number
    lng: number
    address: string
  } | null
  target_m: number
  max_m: number | null
  options: RouteOption[]
  night: boolean
}

export function planWalk(body: {
  lat: number
  lng: number
  text?: string
  minutes?: number
  distance_km?: number
  preference?: WalkPreference
  stops?: WalkStopCategory[]
  departure_time?: string
}): Promise<WalkPlanResult> {
  return gildleFetch("/walk/plan", { method: "POST", body: JSON.stringify(body) })
}
