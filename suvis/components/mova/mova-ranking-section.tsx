import Link from "next/link"
import { Info } from "lucide-react"
import { DragScrollRow } from "@/components/mova/drag-scroll-row"
import { MovaPlatformBadge } from "@/components/mova/mova-platform-badge"
import { MovaRankingPoster } from "@/components/mova/mova-ranking-poster"
import type { MovaHotRankingItem } from "@/lib/mova-api"
import { cn } from "@/lib/utils"

function rankLabelClass(rank: number) {
  if (rank === 1) return "text-mova-accent-bright"
  if (rank <= 3) return "text-amber-400"
  return "text-neutral-500"
}

type MovaRankingSectionProps = {
  variant?: "carousel" | "sidebar"
  items: MovaHotRankingItem[]
  title?: string
}

export function MovaRankingSection({
  variant = "carousel",
  items,
  title,
}: MovaRankingSectionProps) {
  if (!items.length) return null

  const heading =
    title ?? (variant === "sidebar" ? "Mova HOT 랭킹" : "지금 뜨는 작품")

  if (variant === "sidebar") {
    return (
      <aside id="movies" className="scroll-mt-20 lg:sticky lg:top-[4.5rem]">
        <div className="overflow-hidden rounded-xl border border-mova-border bg-mova-surface">
          <div className="border-b border-mova-border px-4 py-3">
            <div className="flex items-center gap-2">
              <h2 className="font-display text-base font-bold text-mova-text">{heading}</h2>
              <button
                type="button"
                aria-label="랭킹 안내"
                className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
              >
                <Info className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-0.5 text-xs text-neutral-500">실시간 인기 1위 ~ 10위</p>
          </div>

          <ol className="max-h-[640px] divide-y divide-mova-border overflow-y-auto">
            {items.map((item) => (
              <li key={item.id}>
                <Link
                  href={`/mova/title/${item.id}`}
                  className="group flex items-center gap-3 px-3 py-2.5 transition-colors hover:bg-mova-surface-2"
                >
                  <span
                    className={cn(
                      "w-7 shrink-0 text-center text-lg font-bold tabular-nums",
                      rankLabelClass(item.rank),
                    )}
                  >
                    {item.rank}
                  </span>
                  <div className="relative h-[72px] w-[48px] shrink-0 overflow-hidden rounded bg-mova-surface-2">
                    <MovaRankingPoster
                      src={item.poster}
                      alt={item.title}
                      sizes="48px"
                      className="object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                    {item.badge && (
                      <span
                        className={cn(
                          "absolute top-1 right-1 rounded px-1 py-0.5 text-[8px] font-bold",
                          item.badge === "NEW" ? "bg-emerald-600 text-white" : "bg-neutral-600 text-white",
                        )}
                      >
                        {item.badge}
                      </span>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <h3 className="truncate text-sm font-medium text-mova-text group-hover:text-mova-accent-bright">
                        {item.title}
                      </h3>
                      {item.platform && <MovaPlatformBadge platform={item.platform} />}
                    </div>
                    <p className="mt-0.5 text-xs text-neutral-500">
                      {item.year} · ★ {item.rating}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ol>
        </div>
      </aside>
    )
  }

  return (
    <section id="trending" className="scroll-mt-20">
      <div className="mb-4 flex items-center gap-2">
        <h2 className="font-display text-lg font-bold text-mova-text md:text-xl">{heading}</h2>
        <button type="button" aria-label="랭킹 안내" className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300">
          <Info className="h-4 w-4" />
        </button>
      </div>

      <div className="mova-row-fade mova-row-scroll -mx-4 px-4 md:-mx-6 md:px-6">
        <DragScrollRow className="flex cursor-grab gap-2 overflow-x-auto pb-3 md:gap-3">
          {items.map((item) => (
            <Link
              key={item.id}
              href={`/mova/title/${item.id}`}
              className="group relative flex w-[140px] shrink-0 items-end gap-1 md:w-[160px]"
            >
              <span
                className={cn(
                  "font-display pointer-events-none absolute -left-1 bottom-6 z-10 text-[4.5rem] leading-none font-bold text-mova-muted/20 select-none md:text-[5.5rem]",
                  item.rank === 1 && "text-mova-accent/25",
                )}
                aria-hidden
              >
                {item.rank}
              </span>
              <div className="mova-poster-card relative ml-6 aspect-[2/3] w-[108px] overflow-hidden rounded-sm bg-mova-surface-2 shadow-lg md:ml-8 md:w-[120px]">
                <MovaRankingPoster
                  src={item.poster}
                  alt={item.title}
                  sizes="120px"
                  className="object-cover"
                />
                {item.badge && (
                  <span
                    className={cn(
                      "absolute top-1.5 right-1.5 rounded px-1 py-0.5 text-[9px] font-bold",
                      item.badge === "NEW" ? "bg-emerald-600 text-white" : "bg-neutral-600 text-white",
                    )}
                  >
                    {item.badge}
                  </span>
                )}
                {item.platform && (
                  <span className="absolute right-1.5 bottom-1.5">
                    <MovaPlatformBadge platform={item.platform} />
                  </span>
                )}
              </div>
              <div className="mb-1 min-w-0 flex-1 pb-1">
                <h3 className="line-clamp-2 text-sm font-medium text-mova-text">{item.title}</h3>
                <p className="mt-0.5 text-xs text-neutral-500">
                  {item.year} · ★ {item.rating}
                </p>
              </div>
            </Link>
          ))}
        </DragScrollRow>
      </div>
    </section>
  )
}
