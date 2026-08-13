"use client"

import Link from "next/link"
import { useCallback, useEffect, useMemo, useState } from "react"
import { ArrowLeft, Loader2, RotateCcw, Timer } from "lucide-react"
import { MovaHeader } from "@/components/mova/mova-header"
import { MovaRankingPoster } from "@/components/mova/mova-ranking-poster"
import {
  fetchLeaderboard,
  fetchMemoryDeck,
  saveGameScore,
  type Leaderboard,
  type MemoryDeckPair,
} from "@/lib/mova-games-api"
import { getSuvisSession } from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

type Phase = "idle" | "preview" | "playing" | "done"

type Card = {
  key: string
  movieId: number
  kind: "poster" | "title"
  poster_url: string
  title: string
}

const STAGES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as const
const PREVIEW_STAGE_THRESHOLD = 3
const PREVIEW_SECONDS = 3

function shuffle<T>(arr: T[]): T[] {
  const out = arr.slice()
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

function pairsToCards(pairs: MemoryDeckPair[]): Card[] {
  const cards: Card[] = []
  pairs.forEach((p, idx) => {
    cards.push({ key: `p-${idx}-${p.movie_id}`, movieId: p.movie_id, kind: "poster", poster_url: p.poster_url, title: p.title })
    cards.push({ key: `t-${idx}-${p.movie_id}`, movieId: p.movie_id, kind: "title", poster_url: p.poster_url, title: p.title })
  })
  return shuffle(cards)
}

export default function MemoryGamePage() {
  const [phase, setPhase] = useState<Phase>("idle")
  const [stage, setStage] = useState<number>(1)
  const [cards, setCards] = useState<Card[]>([])
  const [flipped, setFlipped] = useState<Set<string>>(new Set())
  const [matched, setMatched] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState(false)
  const [startedAt, setStartedAt] = useState<number>(0)
  const [elapsed, setElapsed] = useState<number>(0)
  const [previewLeft, setPreviewLeft] = useState<number>(0)
  const [loadingDeck, setLoadingDeck] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [leaderboard, setLeaderboard] = useState<Leaderboard | null>(null)
  const [savingScore, setSavingScore] = useState(false)

  const totalPairs = 2 * stage
  const totalCards = 4 * stage

  const startStage = useCallback(async (n: number) => {
    setStage(n)
    setLoadingDeck(true)
    setErrorMsg(null)
    setLeaderboard(null)
    try {
      const deck = await fetchMemoryDeck(n)
      setCards(pairsToCards(deck.pairs))
      setFlipped(new Set())
      setMatched(new Set())
      if (n >= PREVIEW_STAGE_THRESHOLD) {
        setPreviewLeft(PREVIEW_SECONDS)
        setPhase("preview")
      } else {
        setStartedAt(Date.now())
        setElapsed(0)
        setPhase("playing")
      }
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "카드 덱을 불러오지 못했습니다.")
      setPhase("idle")
    } finally {
      setLoadingDeck(false)
    }
  }, [])

  // 프리뷰 카운트다운 → playing 전환
  useEffect(() => {
    if (phase !== "preview") return
    if (previewLeft <= 0) {
      setStartedAt(Date.now())
      setElapsed(0)
      setPhase("playing")
      return
    }
    const id = window.setTimeout(() => setPreviewLeft((v) => v - 1), 1000)
    return () => window.clearTimeout(id)
  }, [phase, previewLeft])

  // 경과 시간 카운터
  useEffect(() => {
    if (phase !== "playing") return
    const id = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000))
    }, 500)
    return () => window.clearInterval(id)
  }, [phase, startedAt])

  // 매칭 완료 검사
  useEffect(() => {
    if (phase !== "playing") return
    if (matched.size === totalCards && totalCards > 0) {
      const finalSec = Math.floor((Date.now() - startedAt) / 1000)
      setElapsed(finalSec)
      setPhase("done")
    }
  }, [matched, totalCards, phase, startedAt])

  useEffect(() => {
    if (phase !== "done") return
    const session = getSuvisSession()
    const finalize = async () => {
      if (session?.token) {
        setSavingScore(true)
        try {
          await saveGameScore({ game_type: "memory", stage, score: elapsed, hints_used: 0 })
        } catch {
          // ignore
        } finally {
          setSavingScore(false)
        }
      }
      try {
        const board = await fetchLeaderboard("memory", { limit: 10 })
        setLeaderboard(board)
      } catch {
        setLeaderboard(null)
      }
    }
    void finalize()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase])

  const handleFlip = (card: Card) => {
    if (phase !== "playing") return
    if (busy) return
    if (matched.has(card.key) || flipped.has(card.key)) return
    if (flipped.size >= 2) return

    const next = new Set(flipped)
    next.add(card.key)
    setFlipped(next)

    if (next.size === 2) {
      const [a, b] = [...next].map((k) => cards.find((c) => c.key === k)!)
      if (a.movieId === b.movieId && a.kind !== b.kind) {
        window.setTimeout(() => {
          setMatched((prev) => {
            const m = new Set(prev)
            m.add(a.key)
            m.add(b.key)
            return m
          })
          setFlipped(new Set())
        }, 450)
      } else {
        setBusy(true)
        window.setTimeout(() => {
          setFlipped(new Set())
          setBusy(false)
        }, 900)
      }
    }
  }

  const gridCols = useMemo(() => {
    if (totalCards <= 8) return "grid-cols-4"
    if (totalCards <= 16) return "grid-cols-4"
    if (totalCards <= 24) return "grid-cols-6"
    return "grid-cols-8"
  }, [totalCards])

  const previewShowAll = phase === "preview"

  return (
    <>
      <MovaHeader />
      <main className="mx-auto max-w-[1000px] space-y-6 px-4 py-6 md:px-6 md:py-8">
        <Link href="/mova/games" className="inline-flex items-center gap-1.5 text-sm text-mova-muted hover:text-mova-text">
          <ArrowLeft className="h-3.5 w-3.5" /> 미니게임
        </Link>

        <header className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-lg font-semibold text-mova-text md:text-xl">카드 뒤집기</h1>
          <div className="flex items-center gap-3 text-sm">
            <span className="rounded-md bg-mova-surface px-2 py-1 text-mova-text ring-1 ring-mova-border">
              {stage}단계 · {totalCards}장
            </span>
            {phase === "playing" && (
              <span className="inline-flex items-center gap-1 rounded-md bg-mova-surface px-2 py-1 text-mova-text ring-1 ring-mova-border">
                <Timer className="h-3.5 w-3.5" /> {elapsed}s
              </span>
            )}
            {phase === "preview" && (
              <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/15 px-2 py-1 text-amber-400 ring-1 ring-amber-500/40">
                외우세요 · {previewLeft}s
              </span>
            )}
          </div>
        </header>

        {phase === "idle" && (
          <section className="space-y-4 rounded-2xl border border-mova-border bg-mova-surface p-6">
            <p className="text-sm text-mova-muted">
              단계를 선택하세요. 포스터 카드와 제목 카드를 짝지어 뒤집으면 됩니다.
              점수 = 단계×1000 + max(0, 500-완료초). 1단계가 아무리 빨라도 10단계는 못 이깁니다.
              {" "}
              <span className="text-amber-400">3단계부터는 시작 전 3초간 카드를 미리 보여드려요.</span>
            </p>
            <div className="grid grid-cols-5 gap-2 md:grid-cols-10">
              {STAGES.map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => void startStage(n)}
                  className="rounded-lg border border-mova-border bg-mova-surface-2 py-3 text-sm font-semibold text-mova-text transition hover:border-mova-accent/50 hover:bg-mova-accent-soft"
                >
                  {n}단계
                  <span className="mt-0.5 block text-[10px] font-normal text-mova-muted">
                    {4 * n}장
                    {n >= PREVIEW_STAGE_THRESHOLD && <span className="text-amber-400"> · 3s 프리뷰</span>}
                  </span>
                </button>
              ))}
            </div>
            {errorMsg && <p className="text-sm text-rose-400">{errorMsg}</p>}
          </section>
        )}

        {(phase === "playing" || phase === "preview") && (
          <section>
            {loadingDeck ? (
              <p className="flex items-center gap-2 text-sm text-mova-muted">
                <Loader2 className="h-4 w-4 animate-spin" /> 덱 불러오는 중…
              </p>
            ) : (
              <div className={cn("grid gap-2 md:gap-3", gridCols)}>
                {cards.map((c) => {
                  const isOpen = previewShowAll || flipped.has(c.key) || matched.has(c.key)
                  return (
                    <FlipCard
                      key={c.key}
                      card={c}
                      isOpen={isOpen}
                      isMatched={matched.has(c.key)}
                      onClick={() => handleFlip(c)}
                    />
                  )
                })}
              </div>
            )}
          </section>
        )}

        {phase === "done" && (
          <section className="space-y-6">
            <ClearPanel
              stage={stage}
              elapsed={elapsed}
              savingScore={savingScore}
              onReplay={() => void startStage(stage)}
              onNext={stage < 10 ? () => void startStage(stage + 1) : undefined}
              onExit={() => setPhase("idle")}
            />
            <MemoryLeaderboardBlock board={leaderboard} />
          </section>
        )}
      </main>
    </>
  )
}

function FlipCard({
  card,
  isOpen,
  isMatched,
  onClick,
}: {
  card: Card
  isOpen: boolean
  isMatched: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isMatched}
      className="relative aspect-[2/3] w-full [perspective:900px]"
    >
      <div
        className={cn(
          "relative h-full w-full rounded-lg shadow-lg transition-transform duration-500 ease-out [transform-style:preserve-3d]",
          isOpen && "[transform:rotateY(180deg)]",
          isMatched && "opacity-70",
        )}
      >
        {/* 뒷면 */}
        <div className="absolute inset-0 flex items-center justify-center overflow-hidden rounded-lg bg-mova-surface-2 text-2xl font-bold text-mova-muted ring-1 ring-mova-border [backface-visibility:hidden] [-webkit-backface-visibility:hidden]">
          ?
        </div>
        {/* 앞면 */}
        <div
          className={cn(
            "absolute inset-0 overflow-hidden rounded-lg ring-1 ring-mova-accent/50 [backface-visibility:hidden] [-webkit-backface-visibility:hidden]",
            "[transform:rotateY(180deg)]",
          )}
        >
          {card.kind === "poster" ? (
            <MovaRankingPoster
              src={card.poster_url}
              alt={card.title}
              sizes="120px"
              className="object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center bg-gradient-to-br from-mova-accent-soft to-mova-surface p-2">
              <p className="line-clamp-4 text-center text-xs font-semibold text-mova-text md:text-sm">
                {card.title}
              </p>
            </div>
          )}
        </div>
      </div>
    </button>
  )
}

function ClearPanel({
  stage,
  elapsed,
  savingScore,
  onReplay,
  onNext,
  onExit,
}: {
  stage: number
  elapsed: number
  savingScore: boolean
  onReplay: () => void
  onNext?: () => void
  onExit: () => void
}) {
  const computed = stage * 1000 + Math.max(0, 500 - elapsed)
  return (
    <div className="rounded-2xl border border-mova-border bg-mova-surface p-6 text-center">
      <p className="text-sm text-mova-muted">{stage}단계 클리어!</p>
      <p className="mt-1 text-4xl font-bold text-mova-text">{computed.toLocaleString()}점</p>
      <p className="mt-1 text-xs text-mova-muted">S{stage} · {elapsed}s</p>
      {savingScore && (
        <p className="mt-2 text-xs text-mova-muted">
          <Loader2 className="mr-1 inline h-3 w-3 animate-spin" /> 기록 저장 중…
        </p>
      )}
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        <button
          type="button"
          onClick={onReplay}
          className="inline-flex h-10 items-center gap-1.5 rounded-lg border border-mova-border bg-mova-surface-2 px-4 text-sm text-mova-text transition hover:border-mova-accent/40"
        >
          <RotateCcw className="h-3.5 w-3.5" /> 같은 단계 재도전
        </button>
        {onNext && (
          <button
            type="button"
            onClick={onNext}
            className="h-10 rounded-lg bg-mova-accent px-5 text-sm font-semibold text-white transition hover:brightness-110"
          >
            다음 단계 {stage + 1} →
          </button>
        )}
        <button
          type="button"
          onClick={onExit}
          className="h-10 rounded-lg border border-mova-border bg-mova-surface-2 px-4 text-sm text-mova-text"
        >
          단계 선택으로
        </button>
      </div>
    </div>
  )
}

function MemoryLeaderboardBlock({ board }: { board: Leaderboard | null }) {
  if (!board) return null
  const loggedIn = getSuvisSession() !== null
  return (
    <section className="rounded-2xl border border-mova-border bg-mova-surface p-5">
      <h2 className="mb-3 text-sm font-semibold text-mova-text">통합 리더보드 TOP 10</h2>
      {board.top.length === 0 ? (
        <p className="text-sm text-mova-muted">아직 기록이 없어요.</p>
      ) : (
        <ol className="space-y-1.5">
          {board.top.map((e) => (
            <li
              key={`${e.rank}-${e.user_id}`}
              className={cn(
                "flex items-center justify-between rounded-lg px-3 py-2 text-sm",
                board.me && board.me.user_id === e.user_id ? "bg-mova-accent-soft text-mova-text" : "text-mova-muted",
              )}
            >
              <span className="flex items-center gap-3">
                <span
                  className={cn(
                    "w-6 text-right font-semibold tabular-nums",
                    e.rank === 1 && "text-amber-400",
                    e.rank === 2 && "text-neutral-300",
                    e.rank === 3 && "text-amber-600",
                    e.rank > 3 && "text-mova-text",
                  )}
                >
                  {e.rank}
                </span>
                <span>{e.nickname || `유저 ${e.user_id}`}</span>
              </span>
              <span className="tabular-nums text-xs">
                {e.computed_score.toLocaleString()}점
                {e.stage !== null && (
                  <span className="ml-1 text-mova-muted">(S{e.stage}·{e.score}s)</span>
                )}
              </span>
            </li>
          ))}
        </ol>
      )}
      {loggedIn && board.me && !board.top.some((e) => e.user_id === board.me?.user_id) && (
        <div className="mt-3 flex items-center justify-between rounded-lg bg-mova-accent-soft px-3 py-2 text-sm text-mova-text">
          <span className="flex items-center gap-3">
            <span className="w-6 text-right font-semibold">{board.me.rank}</span>
            <span>내 최고</span>
          </span>
          <span className="text-xs">
            {board.me.computed_score.toLocaleString()}점
            {board.me.stage !== null && (
              <span className="ml-1 text-mova-muted">(S{board.me.stage}·{board.me.score}s)</span>
            )}
          </span>
        </div>
      )}
      {!loggedIn && <p className="mt-3 text-xs text-mova-muted">로그인하면 내 등수가 저장돼요.</p>}
    </section>
  )
}
