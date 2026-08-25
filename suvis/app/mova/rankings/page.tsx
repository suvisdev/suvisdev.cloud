import type { Metadata } from "next"
import Image from "next/image"
import Link from "next/link"
import { Crown, Medal, Star, TrendingUp } from "lucide-react"
import { MovaHeader } from "@/components/mova/mova-header"
import { fetchMovaRankings, type MovaHotRankingItem } from "@/lib/mova-api"
import { cn } from "@/lib/utils"
import { RankingsRefreshButton } from "./rankings-refresh-button"

export const metadata: Metadata = { title: "HOT 랭킹 — Mova" }

const TABS = [
  { key: "box_office", label: "박스오피스" },
  { key: "chat_trend", label: "AI 검색 TOP" },
] as const

type SourceKey = (typeof TABS)[number]["key"]

function resolveSource(raw: string | undefined): SourceKey {
  return TABS.some((tab) => tab.key === raw) ? (raw as SourceKey) : "box_office"
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

        {items === null ? (
          <p className="py-10 text-center text-sm text-neutral-400">
            일시적으로 랭킹을 불러오지 못했습니다. 새로고침해 주세요.
          </p>
        ) : items.length === 0 ? (
          <p className="py-10 text-center text-sm text-neutral-400">
            아직 랭킹 데이터가 없습니다.
          </p>
        ) : (
          <>
            <Podium top3={items.slice(0, 3)} />
            <ol className="space-y-2">
              {items.slice(3).map((item) => (
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
          </>
        )}
      </main>
    </>
  )
}

type RankingItem = MovaHotRankingItem

// 시상식 podium — 2·1·3 배치, 1위 가운데 크게, 왕관/메달 아이콘.
function Podium({ top3 }: { top3: RankingItem[] }) {
  if (top3.length === 0) return null
  const [first, second, third] = top3
  // 화면상 순서: 2위(좌) · 1위(중) · 3위(우). top3에 없으면 자리 비움.
  const slots: { item: RankingItem | undefined; rank: 1 | 2 | 3 }[] = [
    { item: second, rank: 2 },
    { item: first, rank: 1 },
    { item: third, rank: 3 },
  ]
  return (
    <section className="mb-6 rounded-2xl border border-mova-border bg-gradient-to-b from-amber-500/10 via-mova-surface to-transparent p-5 md:p-8">
      <div className="grid grid-cols-3 items-end gap-3 md:gap-6">
        {slots.map(({ item, rank }) =>
          item ? (
            <PodiumCard key={rank} item={item} rank={rank} />
          ) : (
            <div key={rank} />
          ),
        )}
      </div>
    </section>
  )
}

function PodiumCard({ item, rank }: { item: RankingItem; rank: 1 | 2 | 3 }) {
  // items-end 그리드에서 1위 poster는 큼(w-full), 2·3위는 좁게(w-[78%])
  // → aspect-[2/3] 유지 채 높이가 작아져 자연스러운 시상식 podium 실루엣.
  const meta: Record<
    1 | 2 | 3,
    { badgeColor: string; ringColor: string; posterWidth: string; icon: React.ReactNode; label: string }
  > = {
    1: {
      badgeColor: "bg-amber-400 text-black",
      ringColor: "ring-amber-400/70",
      posterWidth: "w-full",
      icon: <Crown className="h-6 w-6 md:h-7 md:w-7" />,
      label: "1위",
    },
    2: {
      badgeColor: "bg-neutral-300 text-black",
      ringColor: "ring-neutral-300/60",
      posterWidth: "w-[88%] md:w-[90%]",
      icon: <Medal className="h-5 w-5 md:h-6 md:w-6" />,
      label: "2위",
    },
    3: {
      badgeColor: "bg-amber-700 text-white",
      ringColor: "ring-amber-700/60",
      posterWidth: "w-[88%] md:w-[90%]",
      icon: <Medal className="h-5 w-5 md:h-6 md:w-6" />,
      label: "3위",
    },
  }
  const m = meta[rank]
  return (
    <Link
      href={`/mova/title/${item.id}`}
      className="group flex flex-col items-center"
    >
      <span
        className={cn(
          "mb-2 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold shadow md:text-sm",
          m.badgeColor,
        )}
      >
        {m.icon}
        {m.label}
      </span>
      <div
        className={cn(
          "relative aspect-[2/3] overflow-hidden rounded-lg bg-neutral-900 ring-2 shadow-lg transition group-hover:brightness-110",
          m.posterWidth,
          m.ringColor,
        )}
      >
        {item.poster ? (
          <Image src={item.poster} alt={item.title} fill className="object-cover" sizes="(max-width: 768px) 33vw, 260px" />
        ) : null}
      </div>
      <p className="mt-2 line-clamp-2 text-center text-sm font-semibold text-mova-text group-hover:text-mova-accent md:text-base">
        {item.title}
      </p>
      <p className="text-xs text-mova-muted">
        {item.year} · ★ {item.rating.toFixed(1)}
      </p>
    </Link>
  )
}
