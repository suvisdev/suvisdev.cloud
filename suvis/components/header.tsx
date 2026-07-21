"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { LayoutDashboard } from "lucide-react"
import { AuthLoginButton } from "@/components/auth/auth-login-button"
import { HeaderWeather } from "@/components/header-weather"
import { ThemeToggle } from "@/components/theme-toggle"
import { getSuvisSession, SUVIS_SESSION_CHANGED_EVENT } from "@/lib/suvis-session"

const navLinkClass =
  "text-xs font-medium text-neutral-600 transition-colors hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100 md:text-sm"

export function Header() {
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    const syncFromSession = () => setIsAdmin(getSuvisSession()?.role === "admin")
    syncFromSession()
    window.addEventListener(SUVIS_SESSION_CHANGED_EVENT, syncFromSession)
    window.addEventListener("storage", syncFromSession)
    return () => {
      window.removeEventListener(SUVIS_SESSION_CHANGED_EVENT, syncFromSession)
      window.removeEventListener("storage", syncFromSession)
    }
  }, [])

  return (
    <header className="sticky top-0 z-50 w-full bg-[#e8e8e8] px-3 pt-2 dark:bg-[#0d0f14] md:px-5 md:pt-2.5">
      <div className="mx-auto flex h-11 max-w-[1600px] items-center justify-between gap-6 rounded-xl border border-neutral-300/80 bg-white px-4 shadow-sm dark:border-[#252b3b] dark:bg-[#161a24] md:h-12 md:gap-8 md:rounded-2xl md:px-7 lg:px-9">
        <Link
          href="/"
          className="shrink-0 text-base font-bold tracking-tight text-neutral-900 transition-opacity hover:opacity-85 dark:text-neutral-100 md:text-lg"
        >
          Suvis<span className="font-extrabold">dev</span>
        </Link>

        <nav className="hidden flex-1 items-center justify-center gap-8 md:flex lg:gap-10">
          <Link href="/apps" className={navLinkClass}>
            Apps
          </Link>
          <Link href="/contact#about" className={navLinkClass}>
            About
          </Link>
          <Link href="/contact#contact" className={navLinkClass}>
            Contact
          </Link>
        </nav>

        <div className="flex min-w-0 shrink-0 items-center gap-2 sm:gap-2.5 md:gap-4">
          <Link href="/apps" className={`${navLinkClass} md:hidden`}>
            Apps
          </Link>
          <Link href="/lesson" className={`${navLinkClass} sm:hidden`}>
            LESSON
          </Link>

          <div className="group relative hidden sm:block">
            <Link
              href="/lesson"
              className={`${navLinkClass} inline-flex items-center gap-1`}
              aria-haspopup="menu"
            >
              LESSON
              <span aria-hidden>▾</span>
            </Link>
            <div className="invisible absolute right-0 top-full z-50 mt-2 min-w-40 rounded-xl border border-neutral-200 bg-white p-1 opacity-0 shadow-lg transition-all group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100 dark:border-[#252b3b] dark:bg-[#161a24]">
              <Link
                href="/titanic"
                className="block rounded-lg px-3 py-2 text-xs text-neutral-700 transition-colors hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-300 dark:hover:bg-neutral-700 dark:hover:text-neutral-100"
              >
                타이타닉
              </Link>
              <Link
                href="/titanic/data-collection"
                className="block rounded-lg px-3 py-2 text-xs text-neutral-700 transition-colors hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-300 dark:hover:bg-neutral-700 dark:hover:text-neutral-100"
              >
                데이터 수집
              </Link>
            </div>
          </div>

          <AuthLoginButton />

          <ThemeToggle />

          {isAdmin && (
            <Link
              href="/admin"
              className="inline-flex items-center gap-1.5 rounded-lg bg-neutral-900 px-2.5 py-1.5 text-[11px] font-semibold text-white transition-colors hover:bg-neutral-700 dark:bg-neutral-700 dark:hover:bg-neutral-600 md:px-3 md:text-xs"
            >
              <LayoutDashboard className="h-3 w-3 md:h-3.5 md:w-3.5" aria-hidden />
              Admin
            </Link>
          )}

          {/* 좁은 화면: 로그인 우선 — 날씨는 sm 이상에서만 (공간·가독성) */}
          <div className="hidden shrink-0 rounded-full bg-neutral-200/90 px-0.5 py-0.5 dark:bg-neutral-700/90 sm:block">
            <HeaderWeather />
          </div>
        </div>
      </div>
    </header>
  )
}
