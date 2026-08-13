import type { Metadata } from "next"
import { CalendarClock } from "lucide-react"
import { MovaHeader } from "@/components/mova/mova-header"
import { MovaRankingPoster } from "@/components/mova/mova-ranking-poster"
import { fetchUpcoming, type UpcomingMovie } from "@/lib/mova-api"

export const metadata: Metadata = { title: "개봉 예정작 — Mova" }

type Group = { key: string; label: string; items: UpcomingMovie[] }

function groupByMonth(items: UpcomingMovie[]): Group[] {
  const buckets = new Map<string, UpcomingMovie[]>()
  for (const m of items) {
    const key = m.release_date ? m.release_date.slice(0, 7) : "unknown" // YYYY-MM
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key)!.push(m)
  }
  const ordered = [...buckets.entries()].sort(([a], [b]) => {
    if (a === "unknown") return 1
    if (b === "unknown") return -1
    return a.localeCompare(b)
  })
  return ordered.map(([key, list]) => ({
    key,
    label: key === "unknown" ? "개봉일 미정" : `${key.slice(0, 4)}년 ${Number(key.slice(5, 7))}월`,
    items: list,
  }))
}

function formatDay(release_date: string): string {
  if (!release_date) return ""
  const [y, m, d] = release_date.split("-")
  return `${Number(m)}/${Number(d)}`
}

export default async function MovaUpcomingPage() {
  const items = await fetchUpcoming(1)
  const groups = groupByMonth(items)

  return (
    <>
      <MovaHeader />
      <main className="mx-auto max-w-[1200px] space-y-6 px-4 py-5 md:px-6 md:py-8">
        <div className="flex items-center gap-2">
          <CalendarClock className="h-5 w-5 text-mova-accent" />
          <h1 className="text-lg font-bold text-mova-text md:text-xl">한국 개봉 예정작</h1>
          <span className="text-xs text-mova-muted">TMDB · 30분 캐시</span>
        </div>

        {items.length === 0 ? (
          <p className="py-10 text-center text-sm text-neutral-400">
            개봉 예정작을 불러오지 못했습니다.
          </p>
        ) : (
          groups.map((g) => (
            <section key={g.key}>
              <h2 className="mb-3 text-sm font-semibold text-mova-text md:text-base">
                {g.label}
                <span className="ml-2 text-xs font-normal text-mova-muted">{g.items.length}편</span>
              </h2>
              <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 md:gap-4">
                {g.items.map((m) => (
                  <li
                    key={m.tmdb_id}
                    className="overflow-hidden rounded-lg border border-mova-border bg-mova-surface"
                  >
                    <div className="relative aspect-[2/3] w-full overflow-hidden bg-neutral-900">
                      <MovaRankingPoster
                        src={m.poster_url}
                        alt={m.title}
                        sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 16vw"
                        className="object-cover"
                      />
                      {m.release_date && (
                        <span className="absolute right-1.5 top-1.5 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] font-semibold text-white tabular-nums">
                          {formatDay(m.release_date)}
                        </span>
                      )}
                    </div>
                    <div className="space-y-1 p-2.5">
                      <p className="line-clamp-2 text-sm font-medium text-mova-text">{m.title}</p>
                      {m.genres.length > 0 && (
                        <p className="truncate text-[11px] text-neutral-500">
                          {m.genres.join(" · ")}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          ))
        )}
      </main>
    </>
  )
}
