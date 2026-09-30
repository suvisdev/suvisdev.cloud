"use client"

import { useEffect, useRef, type ReactNode } from "react"

/** 가로 스크롤 행에 마우스 드래그 스크롤을 붙이는 래퍼 — 드래그 후 클릭은
 *  캡처 단계에서 막아 카드 Link 오동작(드래그가 내비게이션으로 끝나는 것)을 방지한다. */
export function DragScrollRow({
  className,
  children,
  as = "div",
}: {
  className?: string
  children: ReactNode
  /** 목록(`li` 자식)이면 "ul" */
  as?: "div" | "ul"
}) {
  const ref = useRef<HTMLElement | null>(null)
  const setRef = (el: HTMLElement | null) => {
    ref.current = el
  }

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let dragging = false
    let moved = false
    let startX = 0
    let startLeft = 0

    const onMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return
      dragging = true
      moved = false
      startX = e.pageX
      startLeft = el.scrollLeft
    }
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging) return
      const dx = e.pageX - startX
      if (Math.abs(dx) > 5) moved = true
      if (moved) {
        el.scrollLeft = startLeft - dx
        e.preventDefault()
      }
    }
    const onMouseUp = () => {
      dragging = false
    }
    const onClickCapture = (e: MouseEvent) => {
      if (moved) {
        e.preventDefault()
        e.stopPropagation()
        moved = false
      }
    }
    const onDragStart = (e: Event) => {
      if (dragging) e.preventDefault()
    }

    el.addEventListener("mousedown", onMouseDown)
    window.addEventListener("mousemove", onMouseMove)
    window.addEventListener("mouseup", onMouseUp)
    el.addEventListener("click", onClickCapture, true)
    el.addEventListener("dragstart", onDragStart)
    return () => {
      el.removeEventListener("mousedown", onMouseDown)
      window.removeEventListener("mousemove", onMouseMove)
      window.removeEventListener("mouseup", onMouseUp)
      el.removeEventListener("click", onClickCapture, true)
      el.removeEventListener("dragstart", onDragStart)
    }
  }, [])

  if (as === "ul") {
    return (
      <ul ref={setRef} className={className}>
        {children}
      </ul>
    )
  }
  return (
    <div ref={setRef} className={className}>
      {children}
    </div>
  )
}
