"use client"

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

type MovaPosterRowProps = {
  icon: ReactNode
  title: string
  countLabel: string
  /** 항목이 없을 때 보여 줄 안내. 있으면 children 대신 그린다. */
  empty?: ReactNode
  children: ReactNode
}

/** 포스터 가로 목록 — 좌우 화살표로 넘기고, "전체 보기"로 펼쳐 한눈에 본다.
 *  마우스만 있는 데스크톱에선 가로 스크롤 목록이 넘어가는지 알 수 없어서(2026-09-30 실사용) 만든 것.
 *  끝에 닿은 쪽은 화살표와 흐림을 숨겨 더 볼 것이 있는 방향만 알린다. */
export function MovaPosterRow({ icon, title, countLabel, empty, children }: MovaPosterRowProps) {
  const scroller = useRef<HTMLDivElement>(null)
  const [expanded, setExpanded] = useState(false)
  const [canLeft, setCanLeft] = useState(false)
  const [canRight, setCanRight] = useState(false)

  const measure = useCallback(() => {
    const el = scroller.current
    if (!el) return
    setCanLeft(el.scrollLeft > 4)
    setCanRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4)
  }, [])

  useEffect(() => {
    measure()
    window.addEventListener("resize", measure)
    return () => window.removeEventListener("resize", measure)
  }, [measure, children, expanded])

  // 마우스 휠(세로)을 가로 넘김으로 바꾼다. 끝에 닿으면 가로채지 않아 페이지가 평소처럼 세로로 내려간다.
  // preventDefault가 필요해 React onWheel(passive) 대신 직접 등록한다.
  useEffect(() => {
    const el = scroller.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return
      const atStart = el.scrollLeft <= 0
      const atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 1
      if ((e.deltaY < 0 && atStart) || (e.deltaY > 0 && atEnd)) return
      e.preventDefault()
      el.scrollLeft += e.deltaY
    }
    el.addEventListener("wheel", onWheel, { passive: false })
    return () => el.removeEventListener("wheel", onWheel)
  }, [expanded, empty])

  const page = (direction: 1 | -1) => {
    const el = scroller.current
    if (!el) return
    el.scrollBy({ left: direction * el.clientWidth * 0.8, behavior: "smooth" })
  }

  const overflowing = canLeft || canRight

  return (
    <section>
      <div className="mb-3 flex items-center gap-2">
        {icon}
        <h2 className="text-mova-text text-sm font-semibold">{title}</h2>
        <span className="text-xs text-neutral-500">{countLabel}</span>
        {!empty && (overflowing || expanded) && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            className="hover:text-mova-accent ml-auto text-xs text-neutral-400 transition-colors"
          >
            {expanded ? "접기" : "전체 보기"}
          </button>
        )}
      </div>

      {empty}
      {!empty && expanded && <div className="flex flex-wrap gap-3 md:gap-4">{children}</div>}
      {!empty && !expanded && (
        <div className="relative -mx-4 md:mx-0">
          <div
            ref={scroller}
            onScroll={measure}
            className="flex gap-3 overflow-x-auto px-4 pb-2 md:gap-4 md:px-0"
          >
            {children}
          </div>
          <RowEdge side="left" visible={canLeft} onClick={() => page(-1)} />
          <RowEdge side="right" visible={canRight} onClick={() => page(1)} />
        </div>
      )}
    </section>
  )
}

function RowEdge({
  side,
  visible,
  onClick,
}: {
  side: "left" | "right"
  visible: boolean
  onClick: () => void
}) {
  if (!visible) return null
  const left = side === "left"
  return (
    <>
      <div
        aria-hidden
        className={cn(
          "from-mova-bg pointer-events-none absolute inset-y-0 w-12 to-transparent",
          left ? "left-0 bg-gradient-to-r" : "right-0 bg-gradient-to-l"
        )}
      />
      {/* 터치 화면은 손가락으로 넘기므로 화살표는 데스크톱에서만 */}
      <button
        type="button"
        onClick={onClick}
        aria-label={left ? "이전 목록" : "다음 목록"}
        className={cn(
          "border-mova-border bg-mova-surface/95 text-mova-text hover:border-mova-accent/60 hover:text-mova-accent absolute top-[38%] hidden h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border shadow-lg transition md:flex",
          left ? "left-1" : "right-1"
        )}
      >
        {left ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
    </>
  )
}
