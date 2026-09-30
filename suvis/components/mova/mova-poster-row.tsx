"use client"

import { useEffect, useRef, useState, type ReactNode } from "react"
import { DragScrollRow } from "@/components/mova/drag-scroll-row"
import { cn } from "@/lib/utils"

type MovaPosterRowProps = {
  icon: ReactNode
  title: string
  countLabel: string
  /** 항목이 없을 때 보여 줄 안내. 있으면 children 대신 그린다. */
  empty?: ReactNode
  children: ReactNode
}

/** 마이페이지 포스터 가로 목록 — 영화 탭의 장르 줄과 같은 방식(마우스로 잡아 끌기, 양옆 흐림)이고,
 *  넘치는 줄에는 "전체 보기"로 펼쳐 한눈에 보는 버튼이 붙는다. */
export function MovaPosterRow({ icon, title, countLabel, empty, children }: MovaPosterRowProps) {
  const wrapper = useRef<HTMLDivElement>(null)
  const [expanded, setExpanded] = useState(false)
  const [overflowing, setOverflowing] = useState(false)

  useEffect(() => {
    const measure = () => {
      const row = wrapper.current?.firstElementChild
      if (row) setOverflowing(row.scrollWidth > row.clientWidth + 4)
    }
    measure()
    window.addEventListener("resize", measure)
    return () => window.removeEventListener("resize", measure)
  }, [children, expanded])

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
            className="text-mova-muted hover:text-mova-text ml-auto text-xs transition"
          >
            {expanded ? "접기" : "전체 보기 →"}
          </button>
        )}
      </div>

      {empty}
      {!empty && expanded && <div className="flex flex-wrap gap-3 md:gap-4">{children}</div>}
      {!empty && !expanded && (
        <div
          ref={wrapper}
          className={cn(
            "mova-row-scroll -mx-4 px-4 md:-mx-6 md:px-6",
            // 넘치지 않는 줄은 흐림이 포스터만 가리므로 붙이지 않는다.
            overflowing && "mova-row-fade"
          )}
        >
          <DragScrollRow className="flex cursor-grab gap-3 overflow-x-auto pb-2 md:gap-4">
            {children}
          </DragScrollRow>
        </div>
      )}
    </section>
  )
}
