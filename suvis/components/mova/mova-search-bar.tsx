"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { Search } from "lucide-react"
import { fetchMovaSearch, movaMatchLabel, type MovaSearchResult } from "@/lib/mova-api"
import { searchMovaMovies } from "@/lib/mova-movies"
import { patchState } from "@/lib/form-status"
import { cn } from "@/lib/utils"

type MovaSearchBarProps = {
  className?: string
  inputClassName?: string
  placeholder?: string
  /** Enter 시 매칭 결과가 없을 때 (랜딩 → 메인 등) */
  onEmptySubmit?: (query: string) => void
}

type SearchState = {
  query: string
  results: MovaSearchResult[]
  open: boolean
  loading: boolean
  error: string | null
}

type SearchFormProps = { q: string }

const initialSearch: SearchState = {
  query: "",
  results: [],
  open: false,
  loading: false,
  error: null,
}

export function MovaSearchBar({
  className,
  inputClassName,
  placeholder = "작품, 인물, 키워드 검색",
  onEmptySubmit,
}: MovaSearchBarProps) {
  const router = useRouter()
  const [search, setSearch] = useState<SearchState>(initialSearch)
  const patchSearch = (patch: Partial<SearchState>) => patchState(setSearch, patch)
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const q = search.query.trim()
    if (!q) {
      patchSearch({ results: [], error: null, loading: false })
      return
    }

    patchSearch({ loading: true, error: null })
    const timer = window.setTimeout(async () => {
      try {
        const data = await fetchMovaSearch(q)
        patchSearch({ results: data, loading: false })
      } catch {
        const fallback = searchMovaMovies(q).map((m) => ({
          id: m.id,
          title: m.title,
          year: m.year,
          rating: m.rating,
          poster: m.poster,
          match_type: "title" as const,
        }))
        patchSearch({
          results: fallback,
          loading: false,
          error:
            fallback.length === 0
              ? "검색 결과가 없습니다."
              : "DB 연결 실패 — 로컬 데이터로 표시합니다.",
        })
      }
    }, 280)

    return () => window.clearTimeout(timer)
  }, [search.query])

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        patchSearch({ open: false })
      }
    }
    document.addEventListener("mousedown", onClickOutside)
    return () => document.removeEventListener("mousedown", onClickOutside)
  }, [])

  const goToMovie = useCallback(
    (id: string) => {
      patchSearch({ open: false, query: "" })
      router.push(`/mova/title/${id}`)
    },
    [router],
  )

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const formProps = Object.fromEntries(formData.entries()) as SearchFormProps
    const trimmed = formProps.q.trim()
    if (trimmed && search.results[0]) {
      goToMovie(search.results[0].id)
      return
    }
    if (trimmed && onEmptySubmit) {
      onEmptySubmit(trimmed)
      patchSearch({ open: false })
      return
    }
    if (search.results[0]) goToMovie(search.results[0].id)
  }

  const showDropdown = search.open && search.query.trim().length > 0

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <form onSubmit={onSubmit}>
        <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-neutral-500" />
        <input
          type="search"
          name="q"
          value={search.query}
          onChange={(e) => patchSearch({ query: e.target.value, open: true })}
          onFocus={() => patchSearch({ open: true })}
          placeholder={placeholder}
          className={cn(
            "h-9 w-full min-w-0 rounded-md border border-transparent bg-[var(--mova-surface-2)] pr-3 pl-9 text-sm text-[var(--mova-text)] placeholder:text-neutral-500 outline-none ring-0 focus:border-[var(--mova-accent)]/30 focus:bg-[var(--mova-surface)]",
            inputClassName,
          )}
        />
      </form>

      {showDropdown && (
        <ul className="absolute top-full right-0 z-50 mt-1 max-h-[min(18rem,50vh)] w-[min(100vw-2rem,16rem)] min-w-full overflow-auto rounded-md border border-[var(--mova-border)] bg-[var(--mova-surface)] py-1 shadow-xl sm:w-64">
          {search.loading && (
            <li className="px-3 py-2.5 text-sm text-neutral-500">검색 중…</li>
          )}
          {!search.loading && search.error && search.results.length === 0 && (
            <li className="px-3 py-2.5 text-sm text-neutral-500">{search.error}</li>
          )}
          {!search.loading && search.error && search.results.length > 0 && (
            <li className="border-b border-[var(--mova-border)] px-3 py-2 text-xs text-amber-500/90">
              {search.error}
            </li>
          )}
          {!search.loading &&
            search.results.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => goToMovie(item.id)}
                  className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm text-[var(--mova-text)] hover:bg-[var(--mova-surface-2)]"
                >
                  <span className="line-clamp-1 flex-1 font-medium">{item.title}</span>
                  <span className="shrink-0 text-[10px] text-neutral-500">
                    {movaMatchLabel(item.match_type)}
                  </span>
                  <span className="shrink-0 text-xs text-neutral-500">{item.year}</span>
                </button>
              </li>
            ))}
          {!search.loading && !search.error && search.results.length === 0 && (
            <li className="px-3 py-2.5 text-sm text-neutral-500">검색 결과가 없습니다.</li>
          )}
        </ul>
      )}
    </div>
  )
}
