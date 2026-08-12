"use client"

import { useState } from "react"
import { EyeOff } from "lucide-react"

type SpoilerSpan = { start: number; end: number; text: string }

type MovaSpoilerBodyProps = {
  body: string
  spans: SpoilerSpan[] | undefined | null
  className?: string
  /** true면 스포일러가 하나라도 있을 때 상단에 "스포일러 포함" 배지를 렌더 */
  showBadge?: boolean
}

/**
 * 리뷰 본문에서 AI가 판단한 스포일러 구간을 완전 불투명 블록으로 가린다.
 * 텍스트는 `text-transparent`로 완전히 안 보이게, 배경은 짙은 색으로 채워
 * 호버·드래그·개발자도구 없이는 절대 노출되지 않는다. 클릭 →
 * confirm("스포일러일 수 있습니다. 보시겠습니까?") → yes면 그 스팬만 노출.
 * 구간마다 개별적으로 revealed 상태(전체 노출은 아님).
 */
export function MovaSpoilerBody({
  body,
  spans,
  className,
  showBadge = true,
}: MovaSpoilerBodyProps) {
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
          aria-label="스포일러 문구 — 클릭해서 확인"
          title="클릭하면 스포일러 문구를 확인할 수 있어요"
          // text-transparent로 텍스트 자체를 안 보이게 하고, select-none으로
          // 드래그 복사도 막는다. 호버해도 배경만 살짝 밝아질 뿐 텍스트는
          // 여전히 투명(이전엔 hover:bg-neutral-600만 바꿔서 대비로 글자가
          // 보이던 버그).
          className="mx-0.5 cursor-pointer rounded bg-neutral-700 px-1 align-baseline text-transparent select-none hover:bg-neutral-600 dark:bg-neutral-800 dark:hover:bg-neutral-700"
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

  return (
    <span className={className}>
      {showBadge && (
        <span className="mr-1.5 inline-flex items-center gap-1 rounded-md border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-amber-600 align-middle dark:text-amber-400">
          <EyeOff className="h-3 w-3" />
          스포일러 포함
        </span>
      )}
      {parts}
    </span>
  )
}
