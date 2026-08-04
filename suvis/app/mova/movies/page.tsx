"use client"

import Link from "next/link"
import { useEffect, useRef, useState } from "react"
import { Loader2, Star, TrendingUp } from "lucide-react"
import { MovaHeader } from "@/components/mova/mova-header"
import { MovaRankingPoster } from "@/components/mova/mova-ranking-poster"
import { Button } from "@/components/ui/button"
import {
  fetchMovaMovies,
  fetchHotRankings,
  type ApiMovieRow,
  type MovaHotRankingItem,
} from "@/lib/mova-api"
import { resolveMovaCatalogSlug } from "@/lib/mova-catalog"
import { patchState } from "@/lib/form-status"
import { cn } from "@/lib/utils"

const GENRES = [
  "전체",
  "드라마",
  "액션",
  "로맨스",
  "스릴러",
  "SF",
  "코미디",
  "공포",
  "범죄",
  "애니메이션",
  "다큐멘터리",
  "뮤지컬",
] as const

type GenreTab = (typeof GENRES)[number]

type PageState = {
  items: ApiMovieRow[]
  total: number
  limit: number
  offset: number
  loading: boolean
  loadingMore: boolean
  error: string | null
}

const INITIAL_STATE: PageState = {
  items: [],
  total: 0,
  limit: 24,
  offset: 0,
  loading: true,
  loadingMore: false,
  error: null,
}

function MovieCard({ movie }: { movie: ApiMovieRow }) {
  const catalogId = resolveMovaCatalogSlug(movie.slug, movie.title)
  const platform = movie.platforms[0]?.provider
  return (
    <li>
      <Link
        href={`/mova/title/${catalogId}`}
        className="group block overflow-hidden rounded-lg border border-mova-border bg-mova-surface transition hover:border-mova-accent/40"
      >
        <div className="relative aspect-[2/3] w-full overflow-hidden bg-neutral-900">
          <MovaRankingPoster
            src={movie.poster_url}
            alt={movie.title}
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 16vw"
            className="object-cover transition duration-300 group-hover:scale-105"
          />
        </div>
        <div className="space-y-1 p-2.5">
          <p className="line-clamp-2 text-sm font-medium text-mova-text">{movie.title}</p>
          <div className="flex items-center justify-between gap-2 text-xs text-neutral-400">
            <span>{movie.release_year || "연도미상"}</span>
            <span className="inline-flex items-center gap-0.5">
              <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
              {movie.rating.toFixed(1)}
            </span>
          </div>
          {movie.genres.length > 0 && (
            <p className="truncate text-[11px] text-neutral-500">{movie.genres.join(" · ")}</p>
          )}
          {(platform === "netflix" || platform === "disney") && (
            <p className="text-[11px] capitalize text-neutral-500">{platform}</p>
          )}
        </div>
      </Link>
    </li>
  )
}

function TrendingCard({ item, rank }: { item: MovaHotRankingItem; rank: number }) {
  return (
    <Link
      href={`/mova/title/${item.id}`}
      className="group relative w-[100px] shrink-0 md:w-[112px]"
    >
      <div className="relative aspect-[2/3] overflow-hidden rounded-lg bg-neutral-900 ring-1 ring-mova-border transition group-hover:ring-mova-accent/50">
        <MovaRankingPoster
          src={item.poster}
          alt={item.title}
          sizes="112px"
          className="object-cover transition duration-300 group-hover:scale-105"
        />
        <span className="absolute top-1.5 left-1.5 flex h-5 min-w-5 items-center justify-center rounded bg-mova-accent px-1 text-[11px] font-bold text-white">
          {rank}
        </span>
      </div>
      <p className="mt-1.5 line-clamp-2 text-xs font-medium text-mova-text group-hover:text-mova-accent">
        {item.title}
      </p>
    </Link>
  )
}

export default function MovaMoviesPage() {
  const [activeGenre, setActiveGenre] = useState<GenreTab>("전체")
  const [page, setPage] = useState<PageState>(INITIAL_STATE)
  const [trending, setTrending] = useState<MovaHotRankingItem[]>([])
  const genreRef = useRef<HTMLDivElement>(null)
  const patchPage = (patch: Partial<PageState>) => patchState(setPage, patch)

  const loadMovies = async (genre: GenreTab, offset = 0, append = false) => {
    patchPage({ loading: !append, loadingMore: append, error: null })
    try {
      const data = await fetchMovaMovies(INITIAL_STATE.limit, offset, {
        genre: genre === "전체" ? undefined : genre,
      })
      if (append) {
        setPage((prev) => ({
          ...prev,
          items: [...prev.items, ...data.items],
          total: data.total,
          limit: data.limit,
          offset: data.offset,
          loading: false,
          loadingMore: false,
        }))
      } else {
        patchPage({
          items: data.items,
          total: data.total,
          limit: data.limit,
          offset: data.offset,
          loading: false,
          loadingMore: false,
        })
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "영화 목록을 불러오지 못했습니다."
      patchPage({ error: msg, loading: false, loadingMore: false })
    }
  }

  useEffect(() => {
    void fetchHotRankings(10).then(setTrending)
  }, [])

  useEffect(() => {
    void loadMovies(activeGenre, 0, false)
  }, [activeGenre])

  const handleGenreClick = (genre: GenreTab) => {
    setActiveGenre(genre)
    setPage(INITIAL_STATE)
  }

  const hasMore = page.items.length < page.total

  return (
    <>
      <MovaHeader />
      <main className="mx-auto max-w-[1400px] space-y-6 px-4 py-5 md:px-6 md:py-6">

        {/* 인기 검색 영화 */}
        {trending.length > 0 && (
          <section>
            <div className="mb-3 flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-mova-accent" />
              <h2 className="text-sm font-semibold text-mova-text">인기 검색 영화</h2>
              <span className="text-xs text-neutral-500">AI 채팅 기반</span>
            </div>
            <div className="mova-row-fade -mx-4 px-4 md:-mx-0 md:px-0">
              <div className="flex gap-3 overflow-x-auto pb-2 md:gap-4">
                {trending.map((item, i) => (
                  <TrendingCard key={item.id} item={item} rank={i + 1} />
                ))}
              </div>
            </div>
          </section>
        )}

        {/* 장르 탭 */}
        <section>
          <div className="mb-4 flex items-center justify-between gap-2">
            <h1 className="text-lg font-semibold text-mova-text md:text-xl">영화</h1>
            {!page.loading && (
              <span className="text-xs text-neutral-500">총 {page.total}편</span>
            )}
          </div>

          <div ref={genreRef} className="mova-row-fade -mx-4 px-4 md:-mx-0 md:px-0">
            <div className="flex gap-2 overflow-x-auto pb-2">
              {GENRES.map((genre) => (
                <button
                  key={genre}
                  type="button"
                  onClick={() => handleGenreClick(genre)}
                  className={cn(
                    "shrink-0 rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                    activeGenre === genre
                      ? "border-mova-accent bg-mova-accent text-white"
                      : "border-mova-border bg-mova-surface text-mova-muted hover:border-mova-accent/40 hover:text-mova-text",
                  )}
                >
                  {genre}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* 영화 그리드 */}
        {page.loading ? (
          <p className="flex items-center gap-2 text-sm text-neutral-400">
            <Loader2 className="h-4 w-4 animate-spin" />
            불러오는 중...
          </p>
        ) : page.error ? (
          <div className="space-y-3">
            <p className="text-sm text-rose-400">{page.error}</p>
            <Button type="button" variant="outline" onClick={() => void loadMovies(activeGenre, 0, false)}>
              다시 시도
            </Button>
          </div>
        ) : page.items.length === 0 ? (
          <p className="text-sm text-neutral-400">
            {activeGenre === "전체" ? "등록된 영화가 없습니다." : `${activeGenre} 장르 영화가 없습니다.`}
          </p>
        ) : (
          <>
            <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 md:gap-4">
              {page.items.map((movie) => (
                <MovieCard key={movie.id} movie={movie} />
              ))}
            </ul>
            {hasMore && (
              <div className="flex justify-center pt-2">
                <Button
                  type="button"
                  variant="outline"
                  disabled={page.loadingMore}
                  onClick={() => void loadMovies(activeGenre, page.offset + page.limit, true)}
                >
                  {page.loadingMore ? (
                    <span className="inline-flex items-center gap-1.5">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      불러오는 중
                    </span>
                  ) : (
                    "더 보기"
                  )}
                </Button>
              </div>
            )}
          </>
        )}
      </main>
    </>
  )
}
