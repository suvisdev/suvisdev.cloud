"use client"

import { Suspense, useState } from "react"
import { useRouter } from "next/navigation"
import { MovaIntro } from "@/components/mova/mova-intro"
import { MovaLandingChatBar } from "@/components/mova/mova-landing-chat-bar"
import { MovaLoginButton } from "@/components/mova/mova-login-button"
import { MovaSuvisHomeLink } from "@/components/mova/mova-suvis-home-link"
import { MovaLogo } from "@/components/mova/mova-logo"
import { MovaSearchBar } from "@/components/mova/mova-search-bar"
import { MovaLandingRankings } from "@/components/mova/mova-landing-rankings"
import { ThemeToggle } from "@/components/theme-toggle"

function MovaLandingSearch() {
  const router = useRouter()

  return (
    <MovaSearchBar
      className="relative w-[9.5rem] shrink-0 sm:w-44 md:w-48"
      placeholder="검색"
      inputClassName="h-8 w-full min-w-0 border border-[var(--mova-border)] bg-[var(--mova-surface)] text-xs sm:text-sm"
      onEmptySubmit={(q) => {
        if (q.trim()) {
          router.push(`/mova/main?q=${encodeURIComponent(q.trim())}`)
        }
      }}
    />
  )
}

export default function MovaPage() {
  const [introDone, setIntroDone] = useState(false)

  return (
    <main className="mova-cinema-bg mova-grain relative flex min-h-screen min-w-0 flex-col overflow-x-clip">
      {!introDone && <MovaIntro onDone={() => setIntroDone(true)} />}

      <header className="relative z-20 h-11 shrink-0 sm:h-12">
        <div className="absolute top-3 left-4 z-10 sm:top-3.5 sm:left-6 md:hidden">
          <MovaLogo size="sm" />
        </div>
        <div className="absolute top-3 left-4 z-10 hidden sm:top-3.5 sm:left-6 sm:block">
          <MovaLogo size="md" />
        </div>
        <div className="absolute top-3 right-4 z-10 flex items-center gap-2 sm:top-3.5 sm:right-6 sm:gap-2.5">
          <Suspense
            fallback={
              <div className="h-8 w-[9.5rem] animate-pulse rounded-md bg-[var(--mova-surface)] sm:w-44" />
            }
          >
            <MovaLandingSearch />
          </Suspense>
          <ThemeToggle />
          <MovaSuvisHomeLink />
          <MovaLoginButton />
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-4 py-6 sm:py-8 -mt-6 sm:-mt-10">
        <section
          id="mova-landing-chat"
          className="w-full min-w-0 max-w-2xl -translate-y-2 text-center sm:-translate-y-4"
        >
          <p className="mb-2 text-[10px] font-medium tracking-[0.18em] text-[var(--mova-muted)] uppercase sm:mb-3 sm:text-xs sm:tracking-[0.2em]">
            AI movie concierge
          </p>
          <h1 className="font-display text-2xl font-bold leading-tight tracking-tight text-[var(--mova-text)] sm:text-3xl md:text-5xl">
            지금 볼 영화,
            <br />
            Mova가 찾아줄게.
          </h1>

          <div className="mt-4 sm:mt-5 md:mt-6">
            <Suspense
              fallback={
                <div className="h-[3.25rem] animate-pulse rounded-2xl bg-[var(--mova-surface)]" />
              }
            >
              <MovaLandingChatBar />
            </Suspense>
          </div>
        </section>
      </div>

      <section className="w-full max-w-2xl mx-auto px-4 pb-10 min-w-0">
        <MovaLandingRankings />
      </section>
    </main>
  )
}
