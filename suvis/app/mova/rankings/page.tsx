import type { Metadata } from "next"
import Image from "next/image"
import Link from "next/link"
import { Star, TrendingUp } from "lucide-react"
import { MovaHeader } from "@/components/mova/mova-header"
import { fetchMovaRankings } from "@/lib/mova-api"
import { cn } from "@/lib/utils"
import { RankingsRefreshButton } from "./rankings-refresh-button"

export const metadata: Metadata = { title: "HOT 랭킹 — Mova" }

const TABS = [
  { key: "chat_trend", label: "AI 검색 TOP" },
  { key: "box_office", label: "박스오피스" },
] as const

type SourceKey = (typeof TABS)[number]["key"]

function resolveSource(raw: string | undefined): SourceKey {
  return TABS.some((tab) => tab.key === raw) ? (raw as SourceKey) : "chat_trend"
}

export default async function MovaRankingsPage({
  searchParams,
}: {
  searchParams: Promise<{ source?: string }>
}) {
  const { source: rawSource } = await searchParams
  const source = resolveSource(rawSource)
  const items = await fetchMovaRankings(source, 20)

  return (
    <>
      <MovaHeader />
      <main className="mx-auto max-w-[900px] space-y-5 px-4 py-5 md:px-6 md:py-8">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-mova-accent" />
            <h1 className="text-lg font-bold text-mova-text md:text-xl">HOT 랭킹</h1>
          </div>
          {/* 새로고침은 chat_trend 집계만 지원 (백엔드 refresh) */}
          {source === "chat_trend" && <RankingsRefreshButton source={source} />}
        </div>

        {/* source 탭 — searchParams 기반 SSR 전환 */}
        <div className="flex gap-2">
          {TABS.map((tab) => (
            <Link
              key={tab.key}
              href={`/mova/rankings?source=${tab.key}`}
              scroll={false}
              className={cn(
                "rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                source === tab.key
                  ? "border-mova-accent bg-mova-accent text-white"
                  : "border-mova-border bg-mova-surface text-mova-muted hover:text-mova-text",
              )}
            >
              {tab.label}
            </Link>
          ))}
        </div>

        {items.length === 0 ? (
          <p className="py-10 text-center text-sm text-neutral-400">
            아직 랭킹 데이터가 없습니다.
          </p>
        ) : (
          <ol className="space-y-2">
            {items.map((item) => (
              <li key={item.id}>
                <Link
                  href={`/mova/title/${item.id}`}
                  className="group flex items-center gap-4 rounded-xl border border-mova-border bg-mova-surface p-3 transition hover:border-mova-accent/40 hover:bg-mova-accent-soft md:p-4"
                >
                  {/* 순위 — 1·2·3위 강조 */}
                  <span
                    className={cn(
                      "w-8 shrink-0 text-center text-lg font-bold tabular-nums",
                      item.rank === 1 && "text-amber-400",
                      item.rank === 2 && "text-neutral-300",
                      item.rank === 3 && "text-amber-700",
                      item.rank > 3 && "text-neutral-500",
                    )}
                  >
                    {item.rank}
                  </span>

                  {/* 포스터 */}
                  <div className="relative h-16 w-11 shrink-0 overflow-hidden rounded-md bg-neutral-900">
                    {item.poster ? (
                      <Image
                        src={item.poster}
                        alt={item.title}
                        fill
                        className="object-cover"
                        sizes="44px"
                      />
                    ) : null}
                  </div>

                  {/* 정보 */}
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold text-mova-text group-hover:text-mova-accent">
                      {item.title}
                    </p>
                    <div className="mt-0.5 flex items-center gap-2 text-xs text-neutral-400">
                      <span>{item.year}</span>
                      <span className="inline-flex items-center gap-0.5">
                        <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
                        {item.rating.toFixed(1)}
                      </span>
                      {item.platform && <span className="capitalize">{item.platform}</span>}
                    </div>
                  </div>

                  {item.badge && (
                    <span className="shrink-0 rounded bg-mova-accent px-2 py-0.5 text-[10px] font-bold text-white">
                      {item.badge}
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ol>
        )}
      </main>
    </>
  )
}
