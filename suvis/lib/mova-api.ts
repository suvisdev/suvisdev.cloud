import { resolveMovaCatalogSlug } from "@/lib/mova-catalog"
import type { MovaComment, MovaMovie } from "@/lib/mova-movies"
import { MOVA_RANKING } from "@/lib/mova-movies"
import { coercePosterUrl } from "@/lib/mova-poster"
import { authHeader } from "@/lib/suvis-session"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

const API_BASE =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000"

const POSTER_PLACEHOLDER =
  "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400&q=80"

export type MovaHotRankingItem = {
  id: string
  rank: number
  title: string
  year: string
  poster: string
  rating: number
  platform?: "netflix" | "disney"
  badge?: "NEW" | "AD"
}

export type ApiMovieRow = {
  id: number
  slug: string
  title: string
  release_year: number
  rating: number
  poster_url: string
  platforms: { provider: string; url: string | null; type: string | null }[]
  age_rating: string | null
  genres: string[]
}

export type MovaMovieList = {
  items: ApiMovieRow[]
  total: number
  limit: number
  offset: number
}

export type CollectionMovieRow = {
  id: number
  slug: string
  title: string
  release_year: number
  rating: number
  poster_url: string
  platforms: { provider: string; url: string | null; type: string | null }[]
  age_rating: string | null
  genres: string[]
}

export type MovaSearchResult = {
  id: string
  title: string
  year: string
  rating: number
  poster: string
  match_type: "title" | "person" | "keyword" | "synopsis"
}

export type MovaCollectionItem = {
  id: number
  slug: string
  name: string
  description: string
  movie_count: number
}

export type MovaCollectionList = {
  items: MovaCollectionItem[]
  total: number
  limit: number
  offset: number
}

export type MovaCollectionDetail = {
  id: number
  slug: string
  name: string
  description: string
  movie_count: number
}

export type MovaReviewRow = {
  id: number
  user_id: number
  nickname: string
  movie_id: number
  rating: number
  body: string
  created_at: string
}

export type MovaRatingSummary = {
  movie_id: number
  average_rating: number
  review_count: number
}

const MATCH_LABEL: Record<MovaSearchResult["match_type"], string> = {
  title: "작품",
  person: "인물",
  keyword: "키워드",
  synopsis: "줄거리",
}

export function movaMatchLabel(type: MovaSearchResult["match_type"]) {
  return MATCH_LABEL[type]
}

export async function fetchMovaSearch(query: string): Promise<MovaSearchResult[]> {
  const q = query.trim()
  if (!q) return []

  const res = await fetch(`/api/mova/search?q=${encodeURIComponent(q)}`)
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const detail =
      typeof data === "object" && data && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined
    throw new Error(safeApiErrorMessage(detail, `검색 실패 (${res.status})`, res.status))
  }
  const rows = (await res.json()) as MovaSearchResult[]
  return rows.map((row) => ({
    ...row,
    id: resolveMovaCatalogSlug(row.id, row.title),
  }))
}

function titleFetchUrl(slug: string): string {
  if (typeof window !== "undefined") {
    return `/api/mova/titles/${encodeURIComponent(slug)}`
  }
  const base =
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8000"
  return `${base}/mova/movies/${encodeURIComponent(slug)}`
}

function collectionFetchUrl(path: string): string {
  if (typeof window !== "undefined") {
    return `/api/mova/collections${path}`
  }
  return `${API_BASE}/mova/collections${path}`
}

function rankingsFetchUrl(): string {
  if (typeof window !== "undefined") {
    return `/api/mova/rankings`
  }
  return `${API_BASE}/mova/rankings/hot`
}

function reviewsFetchUrl(path: string): string {
  if (typeof window !== "undefined") {
    return `/api/mova/reviews${path}`
  }
  return `${API_BASE}/mova/reviews${path}`
}

function moviesFetchUrl(query = ""): string {
  if (typeof window !== "undefined") {
    return `/api/mova/movies${query}`
  }
  return `${API_BASE}/mova/movies${query}`
}

type MovieDetailApiRow = {
  id: number
  slug: string
  title: string
  release_year: number
  rating: number
  poster_url: string
  platforms: { provider: string }[]
  age_rating: string | null
  genres: string[]
  synopsis: string | null
  actors: {
    name: string
    role_type: "director" | "actor"
    profile_photo_url: string
    character_name: string | null
  }[]
}

export async function fetchMovaTitle(slug: string): Promise<MovaMovie | null> {
  const res = await fetch(titleFetchUrl(slug), {
    next: { revalidate: 60 },
  })
  if (res.status === 404) return null
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const detail =
      typeof data === "object" && data && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined
    throw new Error(safeApiErrorMessage(detail, `작품 조회 실패 (${res.status})`, res.status))
  }
  const row = (await res.json()) as MovieDetailApiRow
  const poster = coercePosterUrl(row.poster_url) ?? POSTER_PLACEHOLDER
  const platformProvider = row.platforms[0]?.provider
  return {
    movieDbId: row.id,
    id: resolveMovaCatalogSlug(row.slug, row.title),
    title: row.title,
    year: String(row.release_year || ""),
    genres: row.genres ?? [],
    country: "",
    ageRating: row.age_rating ?? "",
    platform:
      platformProvider === "netflix" || platformProvider === "disney"
        ? platformProvider
        : undefined,
    poster,
    backdrop: poster,
    rating: row.rating,
    ratingCount: 0,
    rank: 0,
    synopsis: row.synopsis ?? "",
    ratingDistribution: Array(10).fill(0),
    cast: row.actors.map((a) => ({
      name: a.name,
      role:
        a.role_type === "director"
          ? "감독"
          : a.character_name
            ? `출연 | ${a.character_name}`
            : "출연",
      photo: a.profile_photo_url,
    })),
    comments: [],
    gallery: [],
  }
}

type HotRankingApiRow = {
  rank: number
  slug: string
  title: string
  release_year: number
  rating: number
  poster: string
  platform: string | null
  badge: string | null
}

export async function fetchHotRankings(limit = 10): Promise<MovaHotRankingItem[]> {
  try {
    const sources = ["chat_trend", "box_office"] as const
    let rows: HotRankingApiRow[] = []
    for (const source of sources) {
      const res = await fetch(`${API_BASE}/mova/rankings/hot?source=${source}&limit=${limit}`, {
        next: { revalidate: 120 },
      })
      if (!res.ok) continue
      const data = await res.json()
      rows = (
        Array.isArray(data)
          ? (data as HotRankingApiRow[])
          : ((data as { items?: HotRankingApiRow[] }).items ?? [])
      )
      if (rows.length > 0) break
    }
    if (!rows.length) return staticRankingFallback()
    return rows.map((row) => ({
      id: resolveMovaCatalogSlug(row.slug, row.title),
      rank: row.rank,
      title: row.title,
      year: String(row.release_year || ""),
      poster: coercePosterUrl(row.poster) ?? POSTER_PLACEHOLDER,
      rating: row.rating,
      platform:
        row.platform === "netflix" || row.platform === "disney"
          ? row.platform
          : undefined,
      badge: row.badge === "NEW" || row.badge === "AD" ? row.badge : undefined,
    }))
  } catch {
    return staticRankingFallback()
  }
}

export async function fetchMovaRankings(
  source = "chat_trend",
  limit = 10,
): Promise<MovaHotRankingItem[]> {
  try {
    const res = await fetch(
      `${rankingsFetchUrl()}?source=${encodeURIComponent(source)}&limit=${encodeURIComponent(String(limit))}`,
      { cache: "no-store" },
    )
    if (!res.ok) return []
    const data = await res.json()
    const rows: HotRankingApiRow[] = Array.isArray(data)
      ? (data as HotRankingApiRow[])
      : ((data as { items?: HotRankingApiRow[] }).items ?? [])
    return rows.map((row) => ({
      id: resolveMovaCatalogSlug(row.slug, row.title),
      rank: row.rank,
      title: row.title,
      year: String(row.release_year || ""),
      poster: coercePosterUrl(row.poster) ?? POSTER_PLACEHOLDER,
      rating: row.rating,
      platform:
        row.platform === "netflix" || row.platform === "disney"
          ? row.platform
          : undefined,
      badge: row.badge === "NEW" || row.badge === "AD" ? row.badge : undefined,
    }))
  } catch {
    return []
  }
}

export async function refreshMovaRankings(source = "chat_trend"): Promise<void> {
  const res = await fetch(
    `/api/mova/rankings/refresh?source=${encodeURIComponent(source)}`,
    { method: "POST" },
  )
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const detail =
      typeof data === "object" && data && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined
    throw new Error(safeApiErrorMessage(detail, `랭킹 새로고침 실패 (${res.status})`, res.status))
  }
}

function staticRankingFallback(): MovaHotRankingItem[] {
  return MOVA_RANKING.map((m) => ({
    id: m.id,
    rank: m.rank,
    title: m.title,
    year: m.year,
    poster: coercePosterUrl(m.poster) ?? POSTER_PLACEHOLDER,
    rating: m.rating,
    platform: m.platform,
    badge: m.badge,
  }))
}

export async function fetchMovaMovies(
  limit = 24,
  offset = 0,
  filters?: {
    genre?: string
    release_year?: number
    min_rating?: number
    age_rating?: string
    platform?: string
    sort?: string
  },
): Promise<MovaMovieList> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })
  if (filters?.genre) params.set("genre", filters.genre)
  if (filters?.release_year) params.set("release_year", String(filters.release_year))
  if (filters?.min_rating !== undefined) params.set("min_rating", String(filters.min_rating))
  if (filters?.age_rating) params.set("age_rating", filters.age_rating)
  if (filters?.platform) params.set("platform", filters.platform)
  if (filters?.sort) params.set("sort", filters.sort)

  const res = await fetch(moviesFetchUrl(`?${params.toString()}`), {
    cache: "no-store",
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const detail =
      typeof data === "object" && data && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined
    throw new Error(safeApiErrorMessage(detail, `영화 목록 조회 실패 (${res.status})`, res.status))
  }
  return (await res.json()) as MovaMovieList
}

/** @deprecated use fetchMovaMovies */
export async function fetchMovaMoviesFromApi(limit = 80): Promise<ApiMovieRow[]> {
  try {
    const data = await fetchMovaMovies(limit, 0)
    return data.items
  } catch {
    return []
  }
}

export async function fetchMovaCollections(
  limit = 20,
  offset = 0,
): Promise<MovaCollectionList> {
  const res = await fetch(collectionFetchUrl(`?limit=${limit}&offset=${offset}`), {
    cache: "no-store",
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const detail =
      typeof data === "object" && data && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined
    throw new Error(safeApiErrorMessage(detail, `컬렉션 조회 실패 (${res.status})`, res.status))
  }
  return (await res.json()) as MovaCollectionList
}

export async function createMovaCollection(input: {
  slug: string
  name: string
  description?: string
}): Promise<MovaCollectionDetail> {
  const res = await fetch(collectionFetchUrl(""), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail =
      typeof data === "object" && data && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined
    throw new Error(safeApiErrorMessage(detail, `컬렉션 생성 실패 (${res.status})`, res.status))
  }
  return data as MovaCollectionDetail
}

export async function fetchMovaCollectionDetail(slug: string): Promise<MovaCollectionDetail | null> {
  const res = await fetch(collectionFetchUrl(`/${encodeURIComponent(slug)}`), {
    cache: "no-store",
  })
  if (res.status === 404) return null
  if (!res.ok) return null
  return (await res.json()) as MovaCollectionDetail
}

export async function fetchMovaCollectionMovies(
  slug: string,
  limit = 20,
  offset = 0,
): Promise<{ items: CollectionMovieRow[]; total: number; limit: number; offset: number }> {
  const res = await fetch(
    collectionFetchUrl(`/${encodeURIComponent(slug)}/movies?limit=${limit}&offset=${offset}`),
    { cache: "no-store" },
  )
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const detail =
      typeof data === "object" && data && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined
    throw new Error(
      safeApiErrorMessage(detail, `컬렉션 영화 조회 실패 (${res.status})`, res.status),
    )
  }
  const data = (await res.json()) as {
    items: CollectionMovieRow[]
    total: number
    limit: number
    offset: number
  }
  return data
}

export function movaReviewToComment(row: MovaReviewRow): MovaComment {
  return {
    id: String(row.id),
    user: row.nickname,
    rating: row.rating,
    text: row.body,
    likes: 0,
    commentCount: 0,
  }
}

export async function fetchMovaReviewsByMovie(
  movieId: number,
  limit = 20,
  offset = 0,
): Promise<MovaReviewRow[]> {
  const res = await fetch(
    reviewsFetchUrl(
      `/by-movie/${movieId}?limit=${encodeURIComponent(String(limit))}&offset=${encodeURIComponent(String(offset))}`,
    ),
    { cache: "no-store" },
  )
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const detail =
      typeof data === "object" && data && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined
    throw new Error(safeApiErrorMessage(detail, `리뷰 조회 실패 (${res.status})`, res.status))
  }
  return (await res.json()) as MovaReviewRow[]
}

export async function fetchMovaRating(movieId: number): Promise<MovaRatingSummary | null> {
  const res = await fetch(reviewsFetchUrl(`/rating/${movieId}`), { cache: "no-store" })
  if (res.status === 404) return null
  if (!res.ok) return null
  return (await res.json()) as MovaRatingSummary
}

export async function addReviewActivity(input: {
  movie_id: number
  action_type: "favorite" | "watched" | "click" | "not_interested"
}): Promise<void> {
  const res = await fetch(reviewsFetchUrl("/activity"), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const detail =
      typeof data === "object" && data && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined
    throw new Error(safeApiErrorMessage(detail, `처리 실패 (${res.status})`, res.status))
  }
}

export async function createMovaReview(input: {
  movie_id: number
  rating: number | null
  body: string | null
}): Promise<void> {
  const res = await fetch(reviewsFetchUrl(""), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const detail =
      typeof data === "object" && data && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined
    throw new Error(safeApiErrorMessage(detail, `리뷰 등록 실패 (${res.status})`, res.status))
  }
}

export type WatchlistItem = {
  movie_id: number
  slug: string
  title: string
  release_year: number
  rating: number
  poster_url: string | null
  added_at: string
}

export type WatchlistData = {
  items: WatchlistItem[]
  total: number
}

export async function fetchWatchlist(userId: number): Promise<WatchlistData> {
  const res = await fetch(`/api/mova/watchlist/${userId}`, { cache: "no-store" })
  if (!res.ok) throw new Error(`찜 목록 조회 실패 (${res.status})`)
  return (await res.json()) as WatchlistData
}

export async function checkWatchlist(userId: number, movieId: number): Promise<boolean> {
  const res = await fetch(`/api/mova/watchlist/${userId}/check/${movieId}`, { cache: "no-store" })
  if (!res.ok) return false
  const data = (await res.json()) as { in_watchlist: boolean }
  return data.in_watchlist
}

export async function addToWatchlist(userId: number, movieId: number): Promise<void> {
  const res = await fetch("/api/mova/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, movie_id: movieId }),
  })
  if (!res.ok) throw new Error(`찜 추가 실패 (${res.status})`)
}

export async function removeFromWatchlist(userId: number, movieId: number): Promise<void> {
  const res = await fetch(`/api/mova/watchlist/${userId}/${movieId}`, { method: "DELETE" })
  if (!res.ok) throw new Error(`찜 삭제 실패 (${res.status})`)
}

export type MypagePickItem = {
  pick_id: number
  title: string
  hook: string | null
  slug: string
  poster_url: string | null
  batch_at: string
  feedback: string | null
}

export type MypageSearchItem = {
  refined_query: string
  searched_at: string
}

export type MypageData = {
  nickname: string | null
  preferred_genres: string[]
  recent_picks: MypagePickItem[]
  recent_searches: MypageSearchItem[]
}

export async function fetchMovaMypage(userId: number): Promise<MypageData> {
  const res = await fetch(`/api/mova/mypage/${userId}`, { cache: "no-store" })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const detail =
      typeof data === "object" && data && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined
    throw new Error(safeApiErrorMessage(detail, `마이페이지 조회 실패 (${res.status})`, res.status))
  }
  return (await res.json()) as MypageData
}

export function apiMovieToMovaMovie(row: ApiMovieRow): MovaMovie {
  const poster = coercePosterUrl(row.poster_url) ?? POSTER_PLACEHOLDER
  const platformProvider = row.platforms[0]?.provider
  return {
    movieDbId: row.id,
    id: resolveMovaCatalogSlug(row.slug, row.title),
    title: row.title,
    year: String(row.release_year || ""),
    genres: row.genres ?? [],
    country: "",
    ageRating: row.age_rating ?? "",
    platform:
      platformProvider === "netflix" || platformProvider === "disney"
        ? platformProvider
        : undefined,
    poster,
    backdrop: poster,
    rating: row.rating,
    ratingCount: 0,
    rank: 0,
    synopsis: "",
    ratingDistribution: Array(10).fill(0),
    cast: [],
    comments: [],
    gallery: [],
  }
}
