"use client"

import { Suspense, useEffect, useState } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { MOVA_NAV } from "@/lib/mova-mock-data"
import { MovaLoginButton } from "@/components/mova/mova-login-button"
import { MovaSuvisHomeLink } from "@/components/mova/mova-suvis-home-link"
import { MovaLogo } from "@/components/mova/mova-logo"
import { MovaSearchBar } from "@/components/mova/mova-search-bar"
import { ThemeToggle } from "@/components/theme-toggle"
import { getSuvisSession } from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

function isNavActive(pathname: string, href: string): boolean {
  if (href === "/mova") return pathname === "/mova" || pathname.startsWith("/mova/main")
  return pathname === href || pathname.startsWith(`${href}/`)
}

export function MovaHeader() {
  const pathname = usePathname()
  const router = useRouter()
  const [loggedIn, setLoggedIn] = useState(false)

  useEffect(() => {
    setLoggedIn(getSuvisSession() !== null)
  }, [pathname])

  const nav = MOVA_NAV.filter((item) => item.href !== "/mova/mypage" || loggedIn)

  const goToChatSearch = (q: string) => {
    if (q.trim()) router.push(`/mova/main?q=${encodeURIComponent(q.trim())}`)
  }

  return (
    <header className="sticky top-0 z-50 shrink-0 overflow-x-clip border-b border-mova-border bg-mova-bg/90 backdrop-blur-xl">
      {/* 모바일: 로고(좌상) · 검색·로그인(우상) */}
      <div className="relative mx-auto h-12 max-w-[1400px] md:hidden">
        <div className="absolute top-1/2 left-4 z-10 -translate-y-1/2">
          <MovaLogo size="sm" />
        </div>
        <div className="absolute top-1/2 right-4 z-10 flex -translate-y-1/2 items-center gap-2">
          <Suspense fallback={<div className="h-8 w-36 animate-pulse rounded-md bg-mova-surface-2" />}>
            <MovaSearchBar className="relative w-36 shrink-0" onEmptySubmit={goToChatSearch} />
          </Suspense>
          <ThemeToggle />
          <MovaSuvisHomeLink />
          <MovaLoginButton />
        </div>
      </div>

      {/* 모바일: 네비 */}
      <nav className="mx-auto flex max-w-[1400px] gap-4 overflow-x-auto overscroll-x-contain border-t border-mova-border px-4 py-2 pb-2 [-webkit-overflow-scrolling:touch] md:hidden">
        {nav.map((item) => {
          const active = isNavActive(pathname, item.href)
          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "shrink-0 text-sm",
                active ? "font-semibold text-mova-accent-bright" : "text-neutral-400",
              )}
            >
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* 태블릿·데스크톱 */}
      <div className="relative mx-auto hidden h-14 max-w-[1400px] md:block">
        <div className="absolute top-1/2 left-6 z-10 -translate-y-1/2">
          <MovaLogo size="sm" />
        </div>
        <nav className="absolute top-1/2 left-28 z-10 hidden -translate-y-1/2 items-center gap-4 md:flex lg:gap-5">
            {nav.map((item) => {
              const active = isNavActive(pathname, item.href)
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={cn(
                    "text-sm transition-colors whitespace-nowrap",
                    active
                      ? "mova-nav-active font-semibold text-mova-text"
                      : "text-neutral-400 hover:text-mova-text",
                  )}
                >
                  {item.label}
                </Link>
              )
            })}
        </nav>

        <div className="absolute top-1/2 right-6 z-10 flex -translate-y-1/2 items-center gap-2 sm:gap-3">
          <Suspense
            fallback={
              <div className="h-8 w-40 animate-pulse rounded-md bg-mova-surface-2 sm:w-44" />
            }
          >
            <MovaSearchBar
              className="relative w-40 shrink-0 sm:w-44 md:w-48"
              onEmptySubmit={goToChatSearch}
            />
          </Suspense>
          <ThemeToggle />
          <MovaSuvisHomeLink />
          <MovaLoginButton />
        </div>
      </div>
    </header>
  )
}
