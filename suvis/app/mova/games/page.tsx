"use client"

import Link from "next/link"
import { useEffect, useMemo, useState } from "react"
import { ChevronLeft, ChevronRight, Loader2, Trophy } from "lucide-react"
import { fetchLeaderboard, type GameType, type Leaderboard } from "@/lib/mova-games-api"
import { cn } from "@/lib/utils"

// 게임 카드 — 실제 asset 없이 CSS로 각 게임 특징 시각화.
// 초성: 대형 자음 세 글자. 카드 뒤집기: 겹친 3장 카드.
const GAMES = [
  {
    href: "/mova/games/chosung",
    korTitle: "영화 초성 게임",
    engTitle: "CHOSUNG QUIZ",
    accent: "from-fuchsia-500/30 via-indigo-500/15 to-transparent",
    ring: "ring-fuchsia-500/30",
    render: () => (
      <div className="flex h-full items-center justify-center gap-2 select-none">
        {["ㅇ", "ㅂ", "ㅌ"].map((ch, i) => (
          <span
            key={i}
            className="bg-gradient-to-br from-fuchsia-300 via-fuchsia-400 to-indigo-400 bg-clip-text text-6xl font-black tabular-nums text-transparent drop-shadow-[0_0_24px_rgba(217,70,239,0.35)] md:text-7xl"
            style={{ textShadow: "0 0 40px rgba(217, 70, 239, 0.25)" }}
          >
            {ch}
          </span>
        ))}
      </div>
    ),
  },
  {
    href: "/mova/games/memory",
    korTitle: "카드 뒤집기",
    engTitle: "MEMORY MATCH",
    accent: "from-emerald-500/30 via-teal-500/15 to-transparent",
    ring: "ring-emerald-500/30",
    render: () => (
      <div className="flex h-full items-center justify-center select-none">
        <div className="relative h-32 w-24 md:h-40 md:w-28">
          {[-1, 0, 1].map((i) => (
            <div
              key={i}
              className="absolute inset-0 rounded-lg bg-gradient-to-br from-emerald-400/80 to-teal-500/80 shadow-[0_0_24px_rgba(16,185,129,0.35)] ring-1 ring-emerald-300/40"
              style={{
                transform: `translateX(${i * 12}px) rotate(${i * 5}deg)`,
                zIndex: 3 - Math.abs(i),
              }}
            >
              <div className="flex h-full items-center justify-center text-3xl font-bold text-white/70">
                ?
              </div>
            </div>
          ))}
        </div>
      </div>
    ),
  },
] as const

export default function GamesHubPage() {
  return (
    <>
      <main className="mx-auto max-w-[1200px] px-4 py-5 md:px-6 md:py-8">
        <header className="mb-5">
          <h1 className="text-xl font-semibold text-mova-text md:text-2xl">미니게임</h1>
          <p className="mt-1 text-sm text-mova-muted">
            로그인하면 리더보드에 기록이 남고 내 등수를 볼 수 있어요.
          </p>
        </header>

        <div className="grid gap-6 md:grid-cols-[1fr_320px]">
          <section>
            <p className="mb-3 text-sm font-semibold text-mova-text">미니게임 목록 (2)</p>
            <div className="grid grid-cols-2 gap-3 md:gap-4">
              {GAMES.map((g) => (
                <Link
                  key={g.href}
                  href={g.href}
                  className={cn(
                    "group relative overflow-hidden rounded-2xl border border-mova-border bg-mova-surface transition ring-1 ring-transparent hover:border-mova-accent/40 hover:ring-2",
                    g.ring,
                  )}
                >
                  <div
                    className={cn(
                      "relative aspect-[3/4] w-full overflow-hidden bg-gradient-to-b",
                      g.accent,
                    )}
                  >
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_20%,rgba(255,255,255,0.06),transparent_60%)]" />
                    {g.render()}
                  </div>
                  <div className="border-t border-mova-border bg-mova-surface px-4 py-3">
                    <p className="text-sm font-semibold text-mova-text">{g.korTitle}</p>
                    <p className="text-[10px] tracking-wider text-mova-muted">{g.engTitle}</p>
                  </div>
                </Link>
              ))}
            </div>
          </section>

          <LeaderboardSidebar />
        </div>
      </main>
    </>
  )
}

const TABS: { key: GameType; label: string }[] = [
  { key: "memory", label: "카드 뒤집기" },
  { key: "chosung", label: "초성 퀴즈" },
]

function LeaderboardSidebar() {
  const [tabIdx, setTabIdx] = useState(0)
  const [board, setBoard] = useState<Leaderboard | null>(null)
  const [loading, setLoading] = useState(false)

  const activeTab = TABS[tabIdx]

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchLeaderboard(activeTab.key, { limit: 10 })
      .then((b) => {
        if (!cancelled) setBoard(b)
      })
      .catch(() => {
        if (!cancelled) setBoard(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [activeTab.key])

  // memory 통합 리더보드: computed_score 노출, 상세는 (S{n}·{초}s).
  // chosung: 맞춘 개수(그대로 score) 노출.
  const renderScore = useMemo(() => {
    if (activeTab.key === "memory") {
      return function renderMemoryScore(e: Leaderboard["top"][number]) {
        return (
          <>
            {e.computed_score.toLocaleString()}점
            {e.stage !== null && (
              <span className="ml-1 text-[10px] text-mova-muted">(S{e.stage}·{e.score}s)</span>
            )}
          </>
        )
      }
    }
    return function renderChosungScore(e: Leaderboard["top"][number]) {
      return <>{e.score}개 · 힌트 {e.hints_used}</>
    }
  }, [activeTab.key])

  const shift = (d: 1 | -1) =>
    setTabIdx((i) => (i + d + TABS.length) % TABS.length)

  return (
    <aside className="rounded-2xl border border-mova-border bg-mova-surface p-4 md:sticky md:top-20 md:h-fit">
      <div className="mb-3 flex items-center gap-2">
        <Trophy className="h-4 w-4 text-mova-accent" />
        <h2 className="flex-1 text-sm font-semibold text-mova-text">랭킹</h2>
        <button
          type="button"
          onClick={() => shift(-1)}
          aria-label="이전 게임 랭킹"
          className="rounded-md p-1 text-mova-muted hover:bg-mova-surface-2 hover:text-mova-text"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => shift(1)}
          aria-label="다음 게임 랭킹"
          className="rounded-md p-1 text-mova-muted hover:bg-mova-surface-2 hover:text-mova-text"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div className="mb-3 flex gap-1.5">
        {TABS.map((t, i) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTabIdx(i)}
            className={cn(
              "flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition",
              i === tabIdx
                ? "bg-mova-accent text-white"
                : "bg-mova-surface-2 text-mova-muted hover:text-mova-text",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="flex items-center gap-2 py-4 text-sm text-mova-muted">
          <Loader2 className="h-4 w-4 animate-spin" /> 불러오는 중…
        </p>
      ) : !board || board.top.length === 0 ? (
        <p className="py-4 text-sm text-mova-muted">아직 기록이 없어요.</p>
      ) : (
        <ol className="space-y-1">
          {board.top.map((e) => (
            <li
              key={`${e.rank}-${e.user_id}`}
              className={cn(
                "flex items-center justify-between rounded-md px-2 py-1.5 text-xs",
                board.me && board.me.user_id === e.user_id
                  ? "bg-mova-accent-soft text-mova-text"
                  : "text-mova-muted",
              )}
            >
              <span className="flex items-center gap-2 truncate">
                <span
                  className={cn(
                    "w-5 shrink-0 text-right font-semibold tabular-nums",
                    e.rank === 1 && "text-amber-400",
                    e.rank === 2 && "text-neutral-300",
                    e.rank === 3 && "text-amber-600",
                    e.rank > 3 && "text-mova-text",
                  )}
                >
                  {e.rank}
                </span>
                <span className="truncate">{e.nickname || `유저 ${e.user_id}`}</span>
              </span>
              <span className="shrink-0 tabular-nums">{renderScore(e)}</span>
            </li>
          ))}
        </ol>
      )}

      {board?.me && !board.top.some((e) => e.user_id === board.me?.user_id) && (
        <div className="mt-3 flex items-center justify-between rounded-md bg-mova-accent-soft px-2 py-1.5 text-xs text-mova-text">
          <span className="flex items-center gap-2">
            <span className="w-5 text-right font-semibold tabular-nums">{board.me.rank}</span>
            <span>내 최고</span>
          </span>
          <span className="tabular-nums">{renderScore(board.me)}</span>
        </div>
      )}
    </aside>
  )
}
