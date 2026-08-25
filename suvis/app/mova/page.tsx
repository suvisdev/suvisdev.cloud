"use client"

import { Suspense, useState } from "react"
import { MovaHeader } from "@/components/mova/mova-header"
import { MovaIntro } from "@/components/mova/mova-intro"
import { MovaLandingChatBar } from "@/components/mova/mova-landing-chat-bar"

export default function MovaPage() {
  const [introDone, setIntroDone] = useState(false)

  return (
    <main className="mova-cinema-bg mova-grain relative flex min-h-screen min-w-0 flex-col overflow-x-clip">
      {!introDone && <MovaIntro onDone={() => setIntroDone(true)} />}

      {/* 자체 헤더 마크업(로고 md·left-32·무보더)이 다른 페이지의 공통 헤더와
          미묘하게 달라 보이던 것 — 공통 MovaHeader로 통일 (2026-08-25). */}
      <MovaHeader />

      <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-4 py-6 sm:py-8 -mt-6 sm:-mt-10">
        <section
          id="mova-landing-chat"
          className="w-full min-w-0 max-w-2xl -translate-y-2 text-center sm:-translate-y-4"
        >
          <p className="mb-2 text-[10px] font-medium tracking-[0.18em] text-mova-muted uppercase sm:mb-3 sm:text-xs sm:tracking-[0.2em]">
            AI movie concierge
          </p>
          <h1 className="font-display text-2xl font-bold leading-tight tracking-tight text-mova-text sm:text-3xl md:text-5xl">
            지금 볼 영화,
            <br />
            <span className="bg-gradient-to-r from-mova-accent via-[#e05a8a] to-mova-accent-bright bg-clip-text text-transparent">
              Mova
            </span>
            가 찾아줄게.
          </h1>

          <div className="mt-4 sm:mt-5 md:mt-6">
            <Suspense
              fallback={
                <div className="h-[3.25rem] animate-pulse rounded-2xl bg-mova-surface" />
              }
            >
              <MovaLandingChatBar />
            </Suspense>
          </div>
        </section>
      </div>
    </main>
  )
}
