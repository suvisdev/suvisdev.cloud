"use client"

import { Suspense, useEffect, useState } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { MovaIntro } from "@/components/mova/mova-intro"
import { MovaLandingChatBar } from "@/components/mova/mova-landing-chat-bar"
import { MovaLoginButton } from "@/components/mova/mova-login-button"
import { MovaSuvisHomeLink } from "@/components/mova/mova-suvis-home-link"
import { MovaLogo } from "@/components/mova/mova-logo"
import { MovaSearchBar } from "@/components/mova/mova-search-bar"
import { ThemeToggle } from "@/components/theme-toggle"
import { MOVA_NAV } from "@/lib/mova-mock-data"
import { getSuvisSession } from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

function isNavActive(pathname: string, href: string): boolean {
  if (href === "/mova") return pathname === "/mova"
  return pathname === href || pathname.startsWith(`${href}/`)
}

function MovaLandingSearch() {
  const router = useRouter()

  return (
    <MovaSearchBar
      className="relative w-[9.5rem] shrink-0 sm:w-44 md:w-48"
      placeholder="검색"
      inputClassName="h-8 w-full min-w-0 border border-mova-border bg-mova-surface text-xs sm:text-sm"
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
  const [loggedIn, setLoggedIn] = useState(false)
  const pathname = usePathname()

  useEffect(() => {
    setLoggedIn(getSuvisSession() !== null)
  }, [pathname])

  const nav = MOVA_NAV.filter((item) => item.href !== "/mova/mypage" || loggedIn)

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
        {/* 로고 바로 옆 좌측 정렬 — MovaHeader(공통 헤더)와 같은 배치.
            left-32는 이 페이지 데스크톱 로고가 size="md"(공통 헤더는 "sm")라
            MovaHeader의 left-28보다 한 단계 넓게 잡은 것. */}
        <nav className="absolute top-1/2 left-32 z-10 hidden -translate-y-1/2 items-center gap-5 lg:flex">
          {nav.map((item) => {
            const active = isNavActive(pathname, item.href)
            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "text-sm transition-colors",
                  active
                    ? "mova-nav-active font-semibold text-mova-text"
                    : "text-neutral-300 hover:text-mova-text",
                )}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>
        <div className="absolute top-3 right-4 z-10 flex items-center gap-2 sm:top-3.5 sm:right-6 sm:gap-2.5">
          <Suspense
            fallback={
              <div className="h-8 w-[9.5rem] animate-pulse rounded-md bg-mova-surface sm:w-44" />
            }
          >
            <MovaLandingSearch />
          </Suspense>
          <ThemeToggle />
          <MovaSuvisHomeLink />
          <MovaLoginButton />
        </div>
      </header>

      {/* lg 미만: 헤더 아래 가로 스크롤 네비(MovaHeader의 모바일 네비와 동일 패턴) */}
      <nav className="relative z-20 flex gap-4 overflow-x-auto overscroll-x-contain px-4 pb-2 [-webkit-overflow-scrolling:touch] sm:px-6 lg:hidden">
        {nav.map((item) => {
          const active = isNavActive(pathname, item.href)
          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "shrink-0 text-sm",
                active ? "font-semibold text-mova-accent-bright" : "text-neutral-300",
              )}
            >
              {item.label}
            </Link>
          )
        })}
      </nav>

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
            Mova가 찾아줄게.
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
