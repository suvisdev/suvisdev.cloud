"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"

const INTRO_TEXT = "지금 볼 영화, Mova가 찾아줄게"
const INTRO_MS = 1000
const FADE_MS = 250

export function MovaIntro({ onDone }: { onDone: () => void }) {
  const [exiting, setExiting] = useState(false)
  const doneRef = useRef(false)

  const finish = useCallback(() => {
    if (doneRef.current) return
    doneRef.current = true
    setExiting(true)
    onDone()
  }, [onDone])

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      finish()
      return
    }

    const fadeTimer = setTimeout(() => setExiting(true), INTRO_MS - FADE_MS)
    const doneTimer = setTimeout(finish, INTRO_MS)

    return () => {
      clearTimeout(fadeTimer)
      clearTimeout(doneTimer)
    }
  }, [finish])

  return (
    <button
      type="button"
      className={cn(
        "mova-cinema-bg fixed inset-0 z-50 flex cursor-default flex-col items-center justify-center gap-5 border-0 p-0 transition-opacity duration-[250ms]",
        exiting ? "pointer-events-none opacity-0" : "opacity-100",
      )}
      onClick={finish}
      aria-label="인트로 건너뛰기"
    >
      <svg
        viewBox="0 0 140 120"
        className="mova-intro-icon h-24 w-24 sm:h-28 sm:w-28"
        fill="none"
        stroke="var(--mova-accent)"
        strokeWidth={3.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
      >
        <path
          d="M35 58 H105 a9 9 0 0 1 9 9 V93 a9 9 0 0 1 -9 9 H35 a9 9 0 0 1 -9 -9 V67 a9 9 0 0 1 9 -9 Z"
          pathLength={1}
          className="mova-intro-path [animation-delay:0ms]"
        />
        <g transform="rotate(-9 30 56)">
          <path
            d="M34 40 H106 a6 6 0 0 1 6 6 V50 a6 6 0 0 1 -6 6 H34 a6 6 0 0 1 -6 -6 V46 a6 6 0 0 1 6 -6 Z"
            pathLength={1}
            className="mova-intro-path [animation-delay:80ms]"
          />
          <path
            d="M50 40 L44 56 M70 40 L64 56 M90 40 L84 56"
            pathLength={1}
            className="mova-intro-path [animation-delay:160ms]"
          />
        </g>
      </svg>

      <p className="font-display text-lg font-bold tracking-tight text-mova-text sm:text-xl">
        {INTRO_TEXT}
      </p>
    </button>
  )
}
