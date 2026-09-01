"use client"

import { useEffect } from "react"

/** 문서 캡처 단계 scroll 리스너 하나로 페이지의 모든 스크롤 요소(세로 본문 포함)에
 *  스크롤 중에만 `.is-scrolling`을 붙인다 — 스크롤바 표시는 globals.css가 담당. */
export function ScrollbarAutohide() {
  useEffect(() => {
    const timers = new WeakMap<Element, number>()
    const onScroll = (e: Event) => {
      const el = e.target === document ? document.documentElement : e.target
      if (!(el instanceof Element)) return
      el.classList.add("is-scrolling")
      window.clearTimeout(timers.get(el))
      timers.set(
        el,
        window.setTimeout(() => el.classList.remove("is-scrolling"), 800),
      )
    }
    document.addEventListener("scroll", onScroll, { capture: true, passive: true })
    return () => document.removeEventListener("scroll", onScroll, { capture: true })
  }, [])
  return null
}
