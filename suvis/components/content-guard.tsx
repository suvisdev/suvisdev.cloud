"use client"

import { useEffect } from "react"

function isEditable(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    target.closest("input, textarea, [contenteditable='true']") !== null
  )
}

/** 콘텐츠 무단 복제 억제 — 편집 요소(입력창) 밖에서의 복사·잘라내기·우클릭을
 *  막는다. 텍스트 선택 차단은 globals.css의 user-select가 담당. */
export function ContentGuard() {
  useEffect(() => {
    const block = (e: Event) => {
      if (!isEditable(e.target)) e.preventDefault()
    }
    document.addEventListener("copy", block)
    document.addEventListener("cut", block)
    document.addEventListener("contextmenu", block)
    return () => {
      document.removeEventListener("copy", block)
      document.removeEventListener("cut", block)
      document.removeEventListener("contextmenu", block)
    }
  }, [])
  return null
}
