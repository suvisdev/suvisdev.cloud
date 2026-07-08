import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { ArrowLeft, Star } from "lucide-react"
import { MovaHeader } from "@/components/mova/mova-header"
import { MovaRankingPoster } from "@/components/mova/mova-ranking-poster"
import { fetchMovaCollectionDetail, fetchMovaCollectionMovies } from "@/lib/mova-api"
import { resolveMovaCatalogSlug } from "@/lib/mova-catalog"

type PageProps = { params: Promise<{ slug: string }> }

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const col = await fetchMovaCollectionDetail(slug).catch(() => null)
  return { title: col ? `${col.name} — Mova` : "컬렉션 — Mova" }
}

export default async function MovaCollectionDetailPage({ params }: PageProps) {
  const { slug } = await params

  const [col, moviesData] = await Promise.all([
    fetchMovaCollectionDetail(slug).catch(() => null),
    fetchMovaCollectionMovies(slug, 40, 0).catch(() => null),
  ])

  if (!col) notFound()

  const movies = moviesData?.items ?? []

  return (
    <>
      <MovaHeader />
      <main className="mx-auto max-w-[1400px] px-4 py-6 md:px-6 md:py-8">
        <Link
          href="/mova/collections"
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-neutral-400 transition hover:text-[var(--mova-text)]"
        >
          <ArrowLeft className="h-4 w-4" />
          컬렉션 목록
        </Link>

        <div className="mb-8">
          <h1 className="font-display text-2xl font-bold text-[var(--mova-text)] md:text-3xl">
            {col.name}
          </h1>
          {col.description && (
            <p className="mt-2 text-sm leading-relaxed text-[var(--mova-muted)]">
              {col.description}
            </p>
          )}
          <p className="mt-3 text-xs text-neutral-500">영화 {col.movie_count}편</p>
        </div>

        {movies.length === 0 ? (
          <p className="text-sm text-neutral-400">이 컬렉션에 등록된 영화가 없습니다.</p>
        ) : (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 md:gap-4">
            {movies.map((movie) => {
              const titleSlug = resolveMovaCatalogSlug(movie.slug, movie.title)
              return (
                <li key={movie.id}>
                  <Link
                    href={`/mova/title/${titleSlug}`}
                    className="group block overflow-hidden rounded-lg border border-[var(--mova-border)] bg-[var(--mova-surface)] transition hover:border-[var(--mova-accent)]/40"
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
                      <p className="line-clamp-2 text-sm font-medium text-[var(--mova-text)]">
                        {movie.title}
                      </p>
                      <div className="flex items-center justify-between gap-2 text-xs text-neutral-400">
                        <span>{movie.release_year || "연도미상"}</span>
                        <span className="inline-flex items-center gap-0.5">
                          <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
                          {movie.rating.toFixed(1)}
                        </span>
                      </div>
                      {movie.genres.length > 0 && (
                        <p className="truncate text-[11px] text-neutral-500">
                          {movie.genres.join(" · ")}
                        </p>
                      )}
                    </div>
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </main>
    </>
  )
}
