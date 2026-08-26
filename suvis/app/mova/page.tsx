"use client"

import { Suspense, useState } from "react"
import { MovaIntro } from "@/components/mova/mova-intro"
import { MovaLandingChatBar } from "@/components/mova/mova-landing-chat-bar"

export default function MovaPage() {
  const [introDone, setIntroDone] = useState(false)

  return (
    // 헤더가 레이아웃으로 올라가(2026-08-26) 랜딩은 남은 뷰포트를 flex-1로
    // 채운다 — min-h-screen이면 헤더 높이만큼 스크롤이 생긴다.
    <main className="mova-cinema-bg mova-grain relative flex min-h-0 flex-1 min-w-0 flex-col overflow-x-clip">
      {!introDone && <MovaIntro onDone={() => setIntroDone(true)} />}

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
