"use client"

import Link from "next/link"
import { AuthLoginButton } from "@/components/auth/auth-login-button"

// 오른쪽 상단은 로그인 버튼(로그인 후엔 이름 드롭다운) 하나만 — LESSON·Admin은 그 드롭다운으로 옮겼다(2026-10-01).
export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-neutral-300/80 bg-white px-4 dark:border-[#252b3b] dark:bg-[#161a24] md:px-7 lg:px-9">
      <div className="mx-auto flex h-11 w-full max-w-[1600px] items-center justify-between gap-6 md:h-12 md:gap-8">
        <Link
          href="/"
          className="shrink-0 text-base font-bold tracking-tight text-neutral-900 transition-opacity hover:opacity-85 dark:text-neutral-100 md:text-lg"
        >
          Suvis<span className="font-extrabold">dev</span>
        </Link>

        <div className="flex min-w-0 shrink-0 items-center gap-2 sm:gap-2.5 md:gap-4">
          <AuthLoginButton />
        </div>
      </div>
    </header>
  )
}
