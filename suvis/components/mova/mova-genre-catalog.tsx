import Image from "next/image"
import Link from "next/link"
import { Film } from "lucide-react"
import { MovaPlatformBadge } from "@/components/mova/mova-platform-badge"
import { coercePosterUrl } from "@/lib/mova-poster"
import type { MovaGenreGroup, MovaMovie } from "@/lib/mova-movies"

const POSTER_PLACEHOLDER =
  "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400&q=80"

function MovieCard({ movie }: { movie: MovaMovie }) {
  return (
    <Link
      href={`/mova/title/${movie.id}`}
      className="mova-poster-card group w-[118px] shrink-0 md:w-[132px]"
    >
      <div className="relative aspect-[2/3] overflow-hidden rounded-md bg-[var(--mova-surface-2)] shadow-sm ring-1 ring-[var(--mova-border)] transition-shadow group-hover:shadow-md">
        <Image
          src={coercePosterUrl(movie.poster) ?? POSTER_PLACEHOLDER}
          alt={movie.title}
          fill
          className="object-cover"
          sizes="132px"
        />
        {movie.rank > 0 && (
          <span className="absolute top-1.5 left-1.5 flex h-5 min-w-5 items-center justify-center rounded bg-black/75 px-1 text-[11px] font-bold text-white">
            {movie.rank}
          </span>
        )}
        {movie.badge && (
          <span
            className={`absolute top-1.5 right-1.5 rounded px-1 py-0.5 text-[9px] font-bold ${
              movie.badge === "NEW" ? "bg-emerald-600 text-white" : "bg-neutral-600 text-white"
            }`}
          >
            {movie.badge}
          </span>
        )}
        {movie.platform && (
          <span className="absolute right-1.5 bottom-1.5">
            <MovaPlatformBadge platform={movie.platform} />
          </span>
        )}
      </div>
      <h3 className="mt-2 line-clamp-1 text-sm font-medium text-[var(--mova-text)] group-hover:text-[var(--mova-accent)]">
        {movie.title}
      </h3>
      <p className="mt-0.5 text-xs text-[var(--mova-muted)]">
        {movie.year} · ★ {movie.rating}
      </p>
    </Link>
  )
}

type MovaGenreCatalogProps = {
  groups: MovaGenreGroup[]
  title?: string
  subtitle?: string
}

export function MovaGenreCatalog({
  groups,
  title = "장르별 영화",
  subtitle,
}: MovaGenreCatalogProps) {
  if (groups.length === 0) {
    return (
      <p className="rounded-xl border border-[var(--mova-border)] bg-[var(--mova-surface)] px-6 py-12 text-center text-sm text-[var(--mova-muted)]">
        표시할 작품이 없습니다.
      </p>
    )
  }

  return (
    <div className="space-y-10 md:space-y-12">
      {/* 페이지 헤더 */}
      <div className="flex items-end justify-between gap-4 border-b border-[var(--mova-border)] pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--mova-accent-soft)]">
              <Film className="h-4 w-4 text-[var(--mova-accent)]" />
            </span>
            <h1 className="font-display text-2xl font-bold text-[var(--mova-text)] md:text-3xl">{title}</h1>
          </div>
          {subtitle && (
            <p className="mt-2 text-sm text-[var(--mova-muted)]">{subtitle}</p>
          )}
        </div>
        <p className="shrink-0 text-xs text-[var(--mova-muted)]">{groups.length}개 장르</p>
      </div>

      {/* 장르 섹션 */}
      <div className="space-y-10 md:space-y-12">
        {groups.map(({ genre, movies }, index) => (
          <section key={genre} id={`genre-${genre}`} className="scroll-mt-24">
            {index > 0 && (
              <div className="mb-8 border-t border-[var(--mova-border)] md:mb-10" />
            )}
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <span className="block h-5 w-1 rounded-full bg-[var(--mova-accent)]" />
                <h2 className="font-display text-base font-bold text-[var(--mova-text)] md:text-lg">{genre}</h2>
              </div>
              <span className="rounded-full bg-[var(--mova-accent-soft)] px-2.5 py-0.5 text-xs font-medium text-[var(--mova-accent)]">
                {movies.length}편
              </span>
            </div>
            <div className="mova-row-fade mova-row-scroll -mx-4 px-4 md:-mx-0 md:px-0">
              <div className="flex gap-2.5 overflow-x-auto pb-2 md:gap-3">
                {movies.map((movie) => (
                  <MovieCard key={movie.id} movie={movie} />
                ))}
              </div>
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
