"use client"

import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { Suspense, useEffect, useRef, useState } from "react"

import { DragScrollRow } from "@/components/mova/drag-scroll-row"
import { Loader2, RotateCcw, Star, TrendingUp } from "lucide-react"
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

// DB tags(label) 실측 기준(2026-08-26). "뮤지컬"은 TMDB 장르에 없어
// scripts/tag_musical_genre.py가 키워드 기반으로 백필한다. "음악"은 콘서트
// 실황·음악 다큐 계열. 편수 적은 역사·전쟁·서부·TV영화는 탭 제외.
const GENRES = [
  "전체",
  "드라마",
  "액션",
  "로맨스",
  "스릴러",
  "SF",
  "코미디",
  "모험",
  "판타지",
  "공포",
  "범죄",
  "애니메이션",
  "가족",
  "미스터리",
  "뮤지컬",
  "다큐멘터리",
  "음악",
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
  { value: "popular", label: "인기순" },
  { value: "latest", label: "최신순" },
  { value: "rating", label: "평점순" },
] as const

type SortValue = (typeof SORTS)[number]["value"]

// scripts/backfill_age_rating_platforms_cli.py — TMDB KR release_dates.certification 매핑값과 동일.
const AGE_RATINGS = [
  { value: "", label: "전체 등급" },
  { value: "전체", label: "전체 관람가" },
  { value: "12세", label: "12세 이상" },
  { value: "15세", label: "15세 이상" },
  { value: "청불", label: "청소년 관람불가" },
] as const

type AgeRatingValue = (typeof AGE_RATINGS)[number]["value"]

// scripts/backfill_age_rating_platforms_cli.py — TMDB provider_name을 소문자·공백
// 제거로 정규화한 값과 동일해야 매칭된다(tmdb_mapper.py _normalize_provider_key).
const PLATFORMS = [
  { value: "", label: "전체 플랫폼" },
  { value: "netflix", label: "Netflix" },
  { value: "disneyplus", label: "Disney+" },
  { value: "wavve", label: "Wavve" },
  { value: "tving", label: "Tving" },
  { value: "watcha", label: "Watcha" },
  { value: "coupangplay", label: "Coupang Play" },
  { value: "amazonprimevideo", label: "Prime Video" },
  { value: "appletvplus", label: "Apple TV+" },
] as const

type PlatformValue = (typeof PLATFORMS)[number]["value"]

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
            sizes="(max-width: 640px) 33vw, (max-width: 768px) 25vw, (max-width: 1024px) 20vw, (max-width: 1280px) 14vw, 12vw"
            className="object-cover transition duration-300 group-hover:scale-105"
          />
        </div>
        <div className="space-y-0.5 p-1.5">
          <p className="line-clamp-2 text-xs font-medium text-mova-text">{movie.title}</p>
          <div className="flex items-center justify-between gap-1 text-[10px] text-mova-muted">
            <span>{movie.release_year || "연도미상"}</span>
            <span className="inline-flex items-center gap-0.5">
              <Star className="h-2.5 w-2.5 fill-amber-400 text-amber-400" />
              {movie.rating.toFixed(1)}
            </span>
          </div>
          {movie.genres.length > 0 && (
            <p className="truncate text-[10px] text-mova-muted">{movie.genres.slice(0, 2).join(" · ")}</p>
          )}
        </div>
      </Link>
    </li>
  )
}

function GenreRow({
  genre,
  items,
  onSeeAll,
}: {
  genre: string
  items: ApiMovieRow[]
  onSeeAll: () => void
}) {
  return (
    <section>
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-mova-text md:text-base">{genre}</h3>
        <button
          type="button"
          onClick={onSeeAll}
          className="text-xs text-mova-muted transition hover:text-mova-text"
        >
          더보기 →
        </button>
      </div>
      <div className="mova-row-fade mova-row-scroll -mx-4 px-4 md:-mx-6 md:px-6">
        <DragScrollRow className="flex cursor-grab gap-2 overflow-x-auto pb-2 md:gap-3">
          {items.map((movie) => (
            <GenreRowCard key={movie.id} movie={movie} />
          ))}
        </DragScrollRow>
      </div>
    </section>
  )
}

function GenreRowCard({ movie }: { movie: ApiMovieRow }) {
  const catalogId = resolveMovaCatalogSlug(movie.slug, movie.title)
  return (
    <Link
      href={`/mova/title/${catalogId}`}
      className="group w-[104px] shrink-0 md:w-[120px]"
    >
      <div className="relative aspect-[2/3] overflow-hidden rounded-md bg-neutral-900 ring-1 ring-mova-border transition group-hover:ring-mova-accent/50">
        <MovaRankingPoster
          src={movie.poster_url}
          alt={movie.title}
          sizes="120px"
          className="object-cover transition duration-300 group-hover:scale-105"
        />
      </div>
      <p className="mt-1 line-clamp-2 text-xs font-medium text-mova-text group-hover:text-mova-accent-bright">
        {movie.title}
      </p>
    </Link>
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
  const initialSort = ((searchParams.get("sort") as SortValue) || "popular") as SortValue
  const initialActor = searchParams.get("actor") ?? ""
  const initialAgeRating = (searchParams.get("age_rating") ?? "") as AgeRatingValue
  const initialPlatform = (searchParams.get("platform") ?? "") as PlatformValue

  const [genre, setGenre] = useState<GenreTab>(initialGenre)
  const [decade, setDecade] = useState<DecadeValue>(initialDecade)
  const [minRating, setMinRating] = useState<RatingValue>(initialRating)
  const [sort, setSort] = useState<SortValue>(initialSort)
  const [actorInput, setActorInput] = useState(initialActor)
  const [actor, setActor] = useState(initialActor)
  const [ageRating, setAgeRating] = useState<AgeRatingValue>(initialAgeRating)
  const [platform, setPlatform] = useState<PlatformValue>(initialPlatform)
  const [page, setPage] = useState<PageState>(INITIAL_STATE)
  const [trending, setTrending] = useState<MovaHotRankingItem[]>([])
  const [genreRows, setGenreRows] = useState<{ genre: string; items: ApiMovieRow[] }[]>([])
  const [genreRowsLoading, setGenreRowsLoading] = useState(false)
  const genreRef = useRef<HTMLDivElement>(null)
  const patchPage = (patch: Partial<PageState>) => patchState(setPage, patch)

  const hasActiveFilters =
    genre !== "전체" ||
    decade !== "" ||
    minRating !== "" ||
    sort !== "popular" ||
    actor !== "" ||
    ageRating !== "" ||
    platform !== ""

  // 기본 상태(전체 + 필터 없음)에선 장르별 가로 스크롤 로우 노출(넷플릭스 스타일).
  // 필터가 하나라도 활성되면 기존 평면 그리드로 전환.
  const showGenreRows = !hasActiveFilters

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
    ageRating: AgeRatingValue
    platform: PlatformValue
  }) => {
    const params = new URLSearchParams()
    if (next.genre !== "전체") params.set("genre", next.genre)
    if (next.decade) params.set("decade", next.decade)
    if (next.minRating) params.set("min_rating", next.minRating)
    if (next.sort !== "popular") params.set("sort", next.sort)
    if (next.actor) params.set("actor", next.actor)
    if (next.ageRating) params.set("age_rating", next.ageRating)
    if (next.platform) params.set("platform", next.platform)
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
        age_rating: ageRating || undefined,
        platform: platform || undefined,
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
    if (!showGenreRows) void loadMovies(0, false)
    syncUrl({ genre, decade, minRating, sort, actor, ageRating, platform })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [genre, decade, minRating, sort, actor, ageRating, platform])

  // 장르 로우 데이터: 기본 상태에서만 전체 탭 장르를 병렬로 fetch(각 12편).
  useEffect(() => {
    if (!showGenreRows) return
    let cancelled = false
    setGenreRowsLoading(true)
    const rowGenres = GENRES.filter((g) => g !== "전체")
    void Promise.all(
      rowGenres.map(async (g) => {
        try {
          // 인기 상위 48편 풀에서 12편을 무작위 추출 — 방문할 때마다 같은
          // 영화만 반복 노출되지 않게 로테이션을 준다. 최근 15년 작품을
          // 우선하고(1950~70년대 뜬금 노출 방지), 부족할 때만 전체로 폴백.
          const data = await fetchMovaMovies(48, 0, { genre: g, sort: "popular" })
          const cutoff = new Date().getFullYear() - 15
          const recent = data.items.filter((m) => m.release_year >= cutoff)
          const pool = recent.length >= 12 ? recent : [...data.items]
          for (let i = pool.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1))
            ;[pool[i], pool[j]] = [pool[j], pool[i]]
          }
          return { genre: g, items: pool.slice(0, 12) }
        } catch {
          return { genre: g, items: [] as ApiMovieRow[] }
        }
      }),
    ).then((rows) => {
      if (cancelled) return
      setGenreRows(rows.filter((r) => r.items.length > 0))
      setGenreRowsLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [showGenreRows])

  const updateFilters = (
    patch: Partial<{
      genre: GenreTab
      decade: DecadeValue
      minRating: RatingValue
      sort: SortValue
      actor: string
      ageRating: AgeRatingValue
      platform: PlatformValue
    }>,
  ) => {
    if (patch.genre !== undefined) setGenre(patch.genre)
    if (patch.decade !== undefined) setDecade(patch.decade)
    if (patch.minRating !== undefined) setMinRating(patch.minRating)
    if (patch.sort !== undefined) setSort(patch.sort)
    if (patch.actor !== undefined) setActor(patch.actor)
    if (patch.ageRating !== undefined) setAgeRating(patch.ageRating)
    if (patch.platform !== undefined) setPlatform(patch.platform)
  }

  const resetFilters = () => {
    setActorInput("")
    updateFilters({
      genre: "전체",
      decade: "",
      minRating: "",
      sort: "popular",
      actor: "",
      ageRating: "",
      platform: "",
    })
  }

  const hasMore = page.items.length < page.total

  return (
    <>
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
              <DragScrollRow className="flex cursor-grab gap-3 overflow-x-auto pb-2 md:gap-4">
                {trending.map((item, i) => (
                  <TrendingCard key={item.id} item={item} rank={i + 1} />
                ))}
              </DragScrollRow>
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
            <DragScrollRow className="flex cursor-grab gap-2 overflow-x-auto pb-2">
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
            </DragScrollRow>
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
          <FilterSelect
            label="관람 등급"
            value={ageRating}
            options={AGE_RATINGS}
            onChange={(v) => updateFilters({ ageRating: v })}
          />
          <FilterSelect
            label="OTT 플랫폼"
            value={platform}
            options={PLATFORMS}
            onChange={(v) => updateFilters({ platform: v })}
          />
          {hasActiveFilters && (
            <Button type="button" variant="ghost" size="sm" onClick={resetFilters} className="gap-1.5">
              <RotateCcw className="h-3.5 w-3.5" />
              필터 초기화
            </Button>
          )}
        </section>

        {/* 영화 표시 — 기본 상태: 장르별 로우 / 필터 활성: 평면 그리드 */}
        {showGenreRows ? (
          genreRowsLoading ? (
            <p className="flex items-center gap-2 text-sm text-mova-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
              불러오는 중...
            </p>
          ) : (
            <div className="space-y-6">
              {genreRows.map((row) => (
                <GenreRow
                  key={row.genre}
                  genre={row.genre}
                  items={row.items}
                  onSeeAll={() => updateFilters({ genre: row.genre as GenreTab })}
                />
              ))}
            </div>
          )
        ) : page.loading ? (
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
                  <DragScrollRow className="flex cursor-grab gap-3 overflow-x-auto pb-2 md:gap-4">
                    {trending.slice(0, 8).map((item, i) => (
                      <TrendingCard key={item.id} item={item} rank={i + 1} />
                    ))}
                  </DragScrollRow>
                </div>
              </div>
            )}
          </div>
        ) : (
          <>
            <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-7 xl:grid-cols-8 md:gap-3">
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
