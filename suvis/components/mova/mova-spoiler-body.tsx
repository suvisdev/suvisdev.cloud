"use client"

import { useState } from "react"

type SpoilerSpan = { start: number; end: number; text: string }

type MovaSpoilerBodyProps = {
  body: string
  spans: SpoilerSpan[] | undefined | null
  className?: string
}

/**
 * 리뷰 본문에서 AI가 판단한 스포일러 구간을 블러 처리한다.
 * 클릭 → confirm("스포일러일 수 있습니다. 보시겠습니까?") → yes면 해당 구간만 노출.
 * 구간마다 개별적으로 revealed 상태를 가진다(전체 노출은 아님).
 */
export function MovaSpoilerBody({ body, spans, className }: MovaSpoilerBodyProps) {
  const [revealed, setRevealed] = useState<Set<number>>(new Set())

  const cleanSpans = (spans ?? [])
    .filter((s) => s && s.end > s.start && s.start >= 0 && s.end <= body.length)
    .sort((a, b) => a.start - b.start)

  if (cleanSpans.length === 0) {
    return <span className={className}>{body}</span>
  }

  const handleReveal = (idx: number) => {
    if (revealed.has(idx)) return
    if (!window.confirm("스포일러일 수 있습니다. 보시겠습니까?")) return
    setRevealed((prev) => {
      const next = new Set(prev)
      next.add(idx)
      return next
    })
  }

  const parts: React.ReactNode[] = []
  let cursor = 0
  cleanSpans.forEach((span, i) => {
    if (span.start > cursor) {
      parts.push(<span key={`t-${i}`}>{body.slice(cursor, span.start)}</span>)
    }
    const text = body.slice(span.start, span.end)
    const isRevealed = revealed.has(i)
    parts.push(
      isRevealed ? (
        <span key={`s-${i}`} className="rounded bg-yellow-500/15 px-0.5">
          {text}
        </span>
      ) : (
        <button
          key={`s-${i}`}
          type="button"
          onClick={() => handleReveal(i)}
          aria-label="스포일러 문구 보기"
          title="클릭하면 스포일러 문구를 확인할 수 있어요"
          className="rounded bg-neutral-700 px-1 text-neutral-700 hover:bg-neutral-600 dark:bg-neutral-500 dark:text-neutral-500 dark:hover:bg-neutral-400"
        >
          {text}
        </button>
      ),
    )
    cursor = span.end
  })
  if (cursor < body.length) {
    parts.push(<span key="tail">{body.slice(cursor)}</span>)
  }

  return <span className={className}>{parts}</span>
}
