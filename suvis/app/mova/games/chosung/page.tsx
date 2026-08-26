"use client"

import Link from "next/link"
import { useCallback, useEffect, useRef, useState } from "react"
import { ArrowLeft, Lightbulb, Loader2, RotateCcw, Timer } from "lucide-react"
import {
  fetchLeaderboard,
  fetchNextChosungQuestion,
  normalizeAnswer,
  saveGameScore,
  type ChosungCategory,
  type ChosungQuestion,
  type Leaderboard,
} from "@/lib/mova-games-api"
import { getSuvisSession } from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

const GAME_SECONDS = 60

type Phase = "idle" | "playing" | "done"
type Mode = "timed" | "unlimited"

type HintLevel = 0 | 1 | 2 | 3
// 0: 조밀 초성만
// 1: 원래 띄어쓰기/구두점 유지 + 한/외 태그
// 2: 출연진 5명
// 3: 포스터 1/4

const CATEGORY_LABELS: Record<ChosungCategory, string> = {
  all: "전체",
  kr: "한국 영화",
  foreign: "외국 영화",
}

const MODE_LABELS: Record<Mode, string> = {
  timed: "1분 타임어택",
  unlimited: "시간 무제한",
}

export default function ChosungGamePage() {
  const [phase, setPhase] = useState<Phase>("idle")
  const [category, setCategory] = useState<ChosungCategory>("all")
  const [mode, setMode] = useState<Mode>("timed")
  const [question, setQuestion] = useState<ChosungQuestion | null>(null)
  const [answer, setAnswer] = useState("")
  const [hintLevel, setHintLevel] = useState<HintLevel>(0)
  const [secondsLeft, setSecondsLeft] = useState(GAME_SECONDS)
  const [correctCount, setCorrectCount] = useState(0)
  const [totalHintsUsed, setTotalHintsUsed] = useState(0)
  const [feedback, setFeedback] = useState<"correct" | "wrong" | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [loadingQ, setLoadingQ] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [leaderboard, setLeaderboard] = useState<Leaderboard | null>(null)
  const [savingScore, setSavingScore] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  // 이번 게임 세션 중 이미 나온 movie_id — 재출제 방지. useRef라 re-render 없이 축적.
  const seenIdsRef = useRef<Set<number>>(new Set())

  const loadNext = useCallback(async (cat: ChosungCategory) => {
    setLoadingQ(true)
    setErrorMsg(null)
    try {
      const q = await fetchNextChosungQuestion(cat, [...seenIdsRef.current])
      seenIdsRef.current.add(q.movie_id)
      setQuestion(q)
      setAnswer("")
      setHintLevel(0)
      setFeedback(null)
      setRevealed(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "문제를 불러오지 못했습니다.")
    } finally {
      setLoadingQ(false)
    }
  }, [])

  useEffect(() => {
    if (phase !== "playing" || mode !== "timed") return
    if (secondsLeft <= 0) {
      setPhase("done")
      return
    }
    const t = window.setTimeout(() => setSecondsLeft((v) => v - 1), 1000)
    return () => window.clearTimeout(t)
  }, [phase, mode, secondsLeft])

  useEffect(() => {
    if (phase !== "done") return
    const session = getSuvisSession()
    const finalize = async () => {
      // 무제한 모드는 랭킹에 들어가지 않는다 — 기록 저장을 건너뛴다.
      if (session?.token && mode === "timed") {
        setSavingScore(true)
        try {
          await saveGameScore({
            game_type: "chosung",
            score: correctCount,
            hints_used: totalHintsUsed,
          })
        } catch {
          // 저장 실패는 조용히 무시 — 게임 UX를 막지 않는다.
        } finally {
          setSavingScore(false)
        }
      }
      try {
        const board = await fetchLeaderboard("chosung", { limit: 10 })
        setLeaderboard(board)
      } catch {
        setLeaderboard(null)
      }
    }
    void finalize()
  }, [phase, mode, correctCount, totalHintsUsed])

  const startGame = async () => {
    setCorrectCount(0)
    setTotalHintsUsed(0)
    setSecondsLeft(GAME_SECONDS)
    setLeaderboard(null)
    seenIdsRef.current = new Set()  // 새 게임 시작 시 중복 방지 리스트 초기화
    setPhase("playing")
    await loadNext(category)
  }

  const skipCurrent = async () => {
    await loadNext(category)
  }

  const submitAnswer = async () => {
    if (!question || phase !== "playing") return
    if (!answer.trim()) return
    if (normalizeAnswer(answer) === normalizeAnswer(question.title)) {
      setCorrectCount((c) => c + 1)
      setFeedback("correct")
      setTimeout(() => void loadNext(category), 400)
    } else {
      setFeedback("wrong")
      setTimeout(() => setFeedback(null), 500)
    }
  }

  const useHint = () => {
    if (!question || phase !== "playing") return
    if (hintLevel >= 3) return
    setHintLevel((h) => (h + 1) as HintLevel)
    setTotalHintsUsed((n) => n + 1)
  }

  const HINT_LABELS = ["힌트1(띄어쓰기·한/외)", "힌트2(출연진)", "힌트3(포스터 1/4)"] as const

  return (
    <>
      <main className="mx-auto max-w-[720px] space-y-6 px-4 py-6 md:px-6 md:py-8">
        <Link
          href="/mova/games"
          className="inline-flex items-center gap-1.5 text-sm text-mova-muted hover:text-mova-text"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> 미니게임
        </Link>

        <header className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-mova-text md:text-xl">영화 초성 게임</h1>
            {phase !== "idle" && (
              <span className="rounded-full bg-mova-accent-soft px-2 py-0.5 text-[10px] font-medium text-mova-accent-bright">
                {CATEGORY_LABELS[category]} · {MODE_LABELS[mode]}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="inline-flex items-center gap-1 rounded-md bg-mova-surface px-2 py-1 text-mova-text ring-1 ring-mova-border">
              <Timer className="h-3.5 w-3.5" /> {mode === "timed" ? `${secondsLeft}s` : "무제한"}
            </span>
            <span className="rounded-md bg-mova-surface px-2 py-1 text-mova-text ring-1 ring-mova-border">
              맞힌 개수 {correctCount}
            </span>
          </div>
        </header>

        {phase === "idle" && (
          <section className="space-y-4 rounded-2xl border border-mova-border bg-mova-surface p-6">
            <p className="text-sm text-mova-muted">
              1분 안에 최대한 많이 맞혀보세요. 힌트를 쓸수록 등수에서 뒤로 밀립니다.
              <br />
              힌트 순서: 띄어쓰기·한/외 표기 → 출연진 → 포스터 1/4.
              <br />
              시간 무제한 모드는 랭킹에 반영되지 않습니다.
            </p>
            <div>
              <p className="mb-2 text-xs font-medium text-mova-muted">카테고리</p>
              <div className="flex flex-wrap gap-2">
                {(Object.keys(CATEGORY_LABELS) as ChosungCategory[]).map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setCategory(c)}
                    className={cn(
                      "rounded-full border px-4 py-1.5 text-sm font-medium transition",
                      category === c
                        ? "border-mova-accent bg-mova-accent text-white"
                        : "border-mova-border bg-mova-surface-2 text-mova-muted hover:text-mova-text",
                    )}
                  >
                    {CATEGORY_LABELS[c]}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs font-medium text-mova-muted">모드</p>
              <div className="flex flex-wrap gap-2">
                {(Object.keys(MODE_LABELS) as Mode[]).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMode(m)}
                    className={cn(
                      "rounded-full border px-4 py-1.5 text-sm font-medium transition",
                      mode === m
                        ? "border-mova-accent bg-mova-accent text-white"
                        : "border-mova-border bg-mova-surface-2 text-mova-muted hover:text-mova-text",
                    )}
                  >
                    {MODE_LABELS[m]}
                  </button>
                ))}
              </div>
            </div>
            <button
              type="button"
              onClick={() => void startGame()}
              className="h-11 rounded-lg bg-mova-accent px-6 text-sm font-semibold text-white shadow-lg transition hover:brightness-110"
            >
              게임 시작
            </button>
          </section>
        )}

        {phase === "playing" && (
          <section className="space-y-4 rounded-2xl border border-mova-border bg-mova-surface p-5">
            {loadingQ || !question ? (
              <p className="flex items-center gap-2 text-sm text-mova-muted">
                <Loader2 className="h-4 w-4 animate-spin" /> 문제 불러오는 중…
              </p>
            ) : (
              <>
                <div className="space-y-2">
                  <p
                    className={cn(
                      "text-center font-bold tracking-widest text-mova-text",
                      hintLevel >= 1 ? "text-2xl md:text-3xl" : "text-3xl md:text-5xl",
                    )}
                  >
                    {hintLevel >= 1 ? question.chosung_spaced : question.chosung_condensed}
                  </p>
                  {hintLevel >= 1 && (
                    <p className="text-center text-xs text-mova-accent-bright">
                      {question.is_korean ? "한국영화" : "외국영화"}
                    </p>
                  )}
                </div>

                {hintLevel >= 2 && question.cast_names.length > 0 && (
                  <div className="rounded-lg bg-mova-surface-2 p-3">
                    <p className="mb-1 text-[11px] font-medium text-mova-muted">출연</p>
                    <p className="text-sm text-mova-text">
                      {question.cast_names.slice(0, 5).join(" · ")}
                    </p>
                  </div>
                )}

                {hintLevel >= 3 && question.poster_url && (
                  <div className="flex justify-center">
                    <div className="relative aspect-square w-40 overflow-hidden rounded-lg bg-neutral-900 ring-1 ring-mova-border">
                      {/* 포스터 좌상 1/4만 노출(2/3 비율 포스터의 상단 정사각형 대략치) */}
                      <div
                        className="absolute inset-0"
                        style={{
                          backgroundImage: `url(${question.poster_url})`,
                          backgroundSize: "200% 300%",
                          backgroundPosition: "0% 0%",
                          backgroundRepeat: "no-repeat",
                        }}
                      />
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  <input
                    ref={inputRef}
                    value={answer}
                    onChange={(e) => {
                      setAnswer(e.target.value)
                      setFeedback(null)
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void submitAnswer()
                    }}
                    placeholder="영화 제목 입력"
                    className={cn(
                      "h-11 flex-1 rounded-lg border bg-mova-surface-2 px-4 text-sm text-mova-text outline-none transition",
                      feedback === "wrong"
                        ? "border-rose-500/60 ring-1 ring-rose-500/30"
                        : feedback === "correct"
                          ? "border-emerald-500/60 ring-1 ring-emerald-500/30"
                          : "border-mova-border focus:border-mova-accent/50",
                    )}
                  />
                  <button
                    type="button"
                    onClick={() => void submitAnswer()}
                    className="h-11 rounded-lg bg-mova-accent px-4 text-sm font-semibold text-white transition hover:brightness-110"
                  >
                    제출
                  </button>
                </div>

                {revealed && question && (
                  <p className="rounded-lg bg-mova-accent-soft px-4 py-2 text-center text-sm font-semibold text-mova-accent-bright">
                    정답: {question.title}
                  </p>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={useHint}
                    disabled={hintLevel >= 3}
                    className="inline-flex items-center gap-1.5 rounded-md border border-mova-border bg-mova-surface-2 px-3 py-1.5 text-xs text-mova-text transition hover:border-mova-accent/40 disabled:opacity-40"
                  >
                    <Lightbulb className="h-3.5 w-3.5" />
                    {hintLevel < 3 ? HINT_LABELS[hintLevel as 0 | 1 | 2] : "힌트 모두 사용"}
                  </button>
                  <span className="text-xs text-mova-muted">
                    사용한 힌트 {totalHintsUsed}
                  </span>
                  {mode === "unlimited" && !revealed && (
                    <button
                      type="button"
                      onClick={() => setRevealed(true)}
                      className="inline-flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300"
                    >
                      정답 보기
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => void skipCurrent()}
                    className="ml-auto inline-flex items-center gap-1 text-xs text-mova-muted hover:text-mova-text"
                  >
                    <RotateCcw className="h-3 w-3" /> 다음 문제
                  </button>
                  {mode === "unlimited" && (
                    <button
                      type="button"
                      onClick={() => setPhase("done")}
                      className="text-xs text-mova-muted hover:text-mova-text"
                    >
                      게임 종료
                    </button>
                  )}
                </div>
              </>
            )}
            {errorMsg && <p className="text-sm text-rose-400">{errorMsg}</p>}
          </section>
        )}

        {phase === "done" && (
          <section className="space-y-6">
            <div className="rounded-2xl border border-mova-border bg-mova-surface p-6 text-center">
              <p className="text-sm text-mova-muted">종료!</p>
              <p className="mt-1 text-4xl font-bold text-mova-text">{correctCount}개 정답</p>
              <p className="mt-2 text-xs text-mova-muted">사용한 힌트 {totalHintsUsed}</p>
              {savingScore && (
                <p className="mt-2 text-xs text-mova-muted">
                  <Loader2 className="mr-1 inline h-3 w-3 animate-spin" /> 기록 저장 중…
                </p>
              )}
              <div className="mt-4 flex justify-center gap-2">
                <button
                  type="button"
                  onClick={() => void startGame()}
                  className="h-10 rounded-lg bg-mova-accent px-5 text-sm font-semibold text-white transition hover:brightness-110"
                >
                  다시 하기
                </button>
                <Link
                  href="/mova/games"
                  className="inline-flex h-10 items-center rounded-lg border border-mova-border bg-mova-surface-2 px-5 text-sm text-mova-text transition hover:border-mova-accent/40"
                >
                  나가기
                </Link>
              </div>
            </div>

            <ChosungLeaderboardBlock board={leaderboard} />
          </section>
        )}
      </main>
    </>
  )
}

function ChosungLeaderboardBlock({ board }: { board: Leaderboard | null }) {
  if (!board) return null
  const loggedIn = getSuvisSession() !== null
  return (
    <section className="rounded-2xl border border-mova-border bg-mova-surface p-5">
      <h2 className="mb-3 text-sm font-semibold text-mova-text">리더보드 TOP 10</h2>
      {board.top.length === 0 ? (
        <p className="text-sm text-mova-muted">아직 기록이 없어요.</p>
      ) : (
        <ol className="space-y-1.5">
          {board.top.map((e) => (
            <li
              key={`${e.rank}-${e.user_id}`}
              className={cn(
                "flex items-center justify-between rounded-lg px-3 py-2 text-sm",
                board.me && board.me.user_id === e.user_id
                  ? "bg-mova-accent-soft text-mova-text"
                  : "text-mova-muted",
              )}
            >
              <span className="flex items-center gap-3">
                <span className="w-6 text-right font-semibold text-mova-text">{e.rank}</span>
                <span>{e.nickname || `유저 ${e.user_id}`}</span>
              </span>
              <span className="text-xs">
                {e.score}개 · 힌트 {e.hints_used}
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
            {board.me.score}개 · 힌트 {board.me.hints_used}
          </span>
        </div>
      )}
      {!loggedIn && (
        <p className="mt-3 text-xs text-mova-muted">로그인하면 내 등수가 저장돼요.</p>
      )}
    </section>
  )
}
