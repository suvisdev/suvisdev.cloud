import type { Metadata } from "next"
import { fetchMovaTitle } from "@/lib/mova-api"
import { resolveMovaCatalogSlug } from "@/lib/mova-catalog"
import { findMovaMovie, type MovaMovie } from "@/lib/mova-movies"

/** 일부 환경에서 동적 라우트 세그먼트가 percent-encoding 그대로 전달되는 경우를 보정 */
export function decodeMovaRouteSlug(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

export async function loadMovaTitle(rawSlug: string): Promise<MovaMovie | null> {
  const id = decodeMovaRouteSlug(rawSlug)
  const slug = resolveMovaCatalogSlug(id)
  const staticMovie = findMovaMovie(slug) ?? findMovaMovie(id)

  let apiMovie: MovaMovie | null = null
  try {
    apiMovie =
      (await fetchMovaTitle(slug)) ?? (slug !== id ? await fetchMovaTitle(id) : null)
  } catch {
    apiMovie = null
  }

  if (staticMovie) {
    return {
      ...staticMovie,
      ...(apiMovie ?? {}),
      id: staticMovie.id,
      movieDbId: apiMovie?.movieDbId,
      comments: staticMovie.comments,
    }
  }
  return apiMovie ?? staticMovie ?? null
}

export async function movaTitleMetadata(rawSlug: string): Promise<Metadata> {
  const movie = await loadMovaTitle(rawSlug)
  if (!movie) {
    return { title: "작품을 찾을 수 없음 — Mova" }
  }
  return {
    title: `${movie.title} — Mova`,
    description: movie.synopsis || `${movie.title} 상세 정보`,
  }
}
