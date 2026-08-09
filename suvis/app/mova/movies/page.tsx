"use client"

import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { Suspense, useEffect, useRef, useState } from "react"
import { Loader2, RotateCcw, Star, TrendingUp } from "lucide-react"
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

const DECADES = [
  { value: "", label: "전체 연도" },
  { value: "2020", label: "2020년대" },
  { value: "2010", label: "2010년대" },
  { value: "2000", label: "2000년대" },
  { value: "old", label: "그 이전" },
] as const

type DecadeValue = (typeof DECADES)[number]["value"]

function decadeToYearRange(decade: DecadeValue): { min?: number; max?: number } {
  switch (decade) {
    case "2020":
      return { min: 2020, max: 2029 }
    case "2010":
      return { min: 2010, max: 2019 }
    case "2000":
      return { min: 2000, max: 2009 }
    case "old":
      return { max: 1999 }
    default:
      return {}
  }
}

// rating은 0~5 스케일(백엔드 min_rating ge=0.0/le=5.0) — 실측 분포 기준
// 3.5+/4.0+/4.5+가 각각 절반/상위 12%/상위 0.4% 수준이라 의미 있는 3단계.
const RATINGS = [
  { value: "", label: "전체 평점" },
  { value: "3.5", label: "★ 3.5 이상" },
  { value: "4.0", label: "★ 4.0 이상" },
  { value: "4.5", label: "★ 4.5 이상" },
] as const

type RatingValue = (typeof RATINGS)[number]["value"]

const SORTS = [
  { value: "latest", label: "최신순" },
  { value: "popular", label: "인기순" },
  { value: "rating", label: "평점순" },
] as const

type SortValue = (typeof SORTS)[number]["value"]

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

function isGenreTab(v: string | null): v is GenreTab {
  return (GENRES as readonly string[]).includes(v ?? "")
}

function FilterSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: T
  options: readonly { value: T; label: string }[]
  onChange: (v: T) => void
}) {
  return (
    <select
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value as T)}
      className="rounded-md border border-mova-border bg-mova-surface px-3 py-1.5 text-sm text-mova-text"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  )
}

function MovaMoviesPageInner() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const initialGenre = isGenreTab(searchParams.get("genre")) ? (searchParams.get("genre") as GenreTab) : "전체"
  const initialDecade = (searchParams.get("decade") ?? "") as DecadeValue
  const initialRating = (searchParams.get("min_rating") ?? "") as RatingValue
  const initialSort = ((searchParams.get("sort") as SortValue) || "latest") as SortValue
  const initialActor = searchParams.get("actor") ?? ""

  const [genre, setGenre] = useState<GenreTab>(initialGenre)
  const [decade, setDecade] = useState<DecadeValue>(initialDecade)
  const [minRating, setMinRating] = useState<RatingValue>(initialRating)
  const [sort, setSort] = useState<SortValue>(initialSort)
  const [actorInput, setActorInput] = useState(initialActor)
  const [actor, setActor] = useState(initialActor)
  const [page, setPage] = useState<PageState>(INITIAL_STATE)
  const [trending, setTrending] = useState<MovaHotRankingItem[]>([])
  const genreRef = useRef<HTMLDivElement>(null)
  const patchPage = (patch: Partial<PageState>) => patchState(setPage, patch)

  const hasActiveFilters =
    genre !== "전체" || decade !== "" || minRating !== "" || sort !== "latest" || actor !== ""

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setActor(actorInput.trim())
    }, 400)
    return () => window.clearTimeout(timer)
  }, [actorInput])

  const syncUrl = (next: {
    genre: GenreTab
    decade: DecadeValue
    minRating: RatingValue
    sort: SortValue
    actor: string
  }) => {
    const params = new URLSearchParams()
    if (next.genre !== "전체") params.set("genre", next.genre)
    if (next.decade) params.set("decade", next.decade)
    if (next.minRating) params.set("min_rating", next.minRating)
    if (next.sort !== "latest") params.set("sort", next.sort)
    if (next.actor) params.set("actor", next.actor)
    const qs = params.toString()
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }

  const loadMovies = async (offset: number, append: boolean) => {
    patchPage({ loading: !append, loadingMore: append, error: null })
    const { min, max } = decadeToYearRange(decade)
    try {
      const data = await fetchMovaMovies(INITIAL_STATE.limit, offset, {
        genre: genre === "전체" ? undefined : genre,
        actor: actor || undefined,
        release_year_min: min,
        release_year_max: max,
        min_rating: minRating ? Number(minRating) : undefined,
        sort,
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
    setPage(INITIAL_STATE)
    void loadMovies(0, false)
    syncUrl({ genre, decade, minRating, sort, actor })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [genre, decade, minRating, sort, actor])

  const updateFilters = (
    patch: Partial<{ genre: GenreTab; decade: DecadeValue; minRating: RatingValue; sort: SortValue; actor: string }>,
  ) => {
    if (patch.genre !== undefined) setGenre(patch.genre)
    if (patch.decade !== undefined) setDecade(patch.decade)
    if (patch.minRating !== undefined) setMinRating(patch.minRating)
    if (patch.sort !== undefined) setSort(patch.sort)
    if (patch.actor !== undefined) setActor(patch.actor)
  }

  const resetFilters = () => {
    setActorInput("")
    updateFilters({ genre: "전체", decade: "", minRating: "", sort: "latest", actor: "" })
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
              {GENRES.map((g) => (
                <button
                  key={g}
                  type="button"
                  onClick={() => updateFilters({ genre: g })}
                  className={cn(
                    "shrink-0 rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                    genre === g
                      ? "border-mova-accent bg-mova-accent text-white"
                      : "border-mova-border bg-mova-surface text-mova-muted hover:border-mova-accent/40 hover:text-mova-text",
                  )}
                >
                  {g}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* 필터 바 */}
        <section className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            aria-label="배우 이름"
            placeholder="배우 이름"
            value={actorInput}
            onChange={(e) => setActorInput(e.target.value)}
            className="w-32 rounded-md border border-mova-border bg-mova-surface px-3 py-1.5 text-sm text-mova-text placeholder:text-mova-muted"
          />
          <FilterSelect label="연도" value={decade} options={DECADES} onChange={(v) => updateFilters({ decade: v })} />
          <FilterSelect label="평점" value={minRating} options={RATINGS} onChange={(v) => updateFilters({ minRating: v })} />
          <FilterSelect label="정렬" value={sort} options={SORTS} onChange={(v) => updateFilters({ sort: v })} />
          <select
            aria-label="관람 등급"
            disabled
            title="데이터 준비 중입니다"
            className="cursor-not-allowed rounded-md border border-mova-border bg-mova-surface px-3 py-1.5 text-sm text-mova-muted opacity-50"
          >
            <option>관람 등급 (준비 중)</option>
          </select>
          <select
            aria-label="OTT 플랫폼"
            disabled
            title="데이터 준비 중입니다"
            className="cursor-not-allowed rounded-md border border-mova-border bg-mova-surface px-3 py-1.5 text-sm text-mova-muted opacity-50"
          >
            <option>OTT 플랫폼 (준비 중)</option>
          </select>
          {hasActiveFilters && (
            <Button type="button" variant="ghost" size="sm" onClick={resetFilters} className="gap-1.5">
              <RotateCcw className="h-3.5 w-3.5" />
              필터 초기화
            </Button>
          )}
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
            <Button type="button" variant="outline" onClick={() => void loadMovies(0, false)}>
              다시 시도
            </Button>
          </div>
        ) : page.items.length === 0 ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm text-neutral-400">조건에 맞는 영화가 없습니다.</p>
              {hasActiveFilters && (
                <Button type="button" variant="outline" size="sm" onClick={resetFilters} className="gap-1.5">
                  <RotateCcw className="h-3.5 w-3.5" />
                  필터 초기화하고 다시 보기
                </Button>
              )}
            </div>
            {trending.length > 0 && (
              <div>
                <p className="mb-2 text-xs text-neutral-500">대신 이런 영화는 어때요?</p>
                <div className="mova-row-fade -mx-4 px-4 md:-mx-0 md:px-0">
                  <div className="flex gap-3 overflow-x-auto pb-2 md:gap-4">
                    {trending.slice(0, 8).map((item, i) => (
                      <TrendingCard key={item.id} item={item} rank={i + 1} />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
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
                  onClick={() => void loadMovies(page.offset + page.limit, true)}
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

export default function MovaMoviesPage() {
  return (
    <Suspense fallback={null}>
      <MovaMoviesPageInner />
    </Suspense>
  )
}
