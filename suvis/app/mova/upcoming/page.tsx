import type { Metadata } from "next"
import { CalendarClock } from "lucide-react"
import { MovaHeader } from "@/components/mova/mova-header"
import { MovaRankingPoster } from "@/components/mova/mova-ranking-poster"
import { fetchUpcoming } from "@/lib/mova-api"

export const metadata: Metadata = { title: "개봉 예정작 — Mova" }

export default async function MovaUpcomingPage() {
  const items = await fetchUpcoming(1)

  return (
    <>
      <MovaHeader />
      <main className="mx-auto max-w-[1200px] space-y-5 px-4 py-5 md:px-6 md:py-8">
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
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 md:gap-4">
            {items.map((m) => (
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
                </div>
                <div className="space-y-1 p-2.5">
                  <p className="line-clamp-2 text-sm font-medium text-mova-text">{m.title}</p>
                  <p className="text-xs text-mova-muted">
                    {m.release_year || "개봉일 미정"}
                  </p>
                  {m.genres.length > 0 && (
                    <p className="truncate text-[11px] text-neutral-500">
                      {m.genres.join(" · ")}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  )
}
