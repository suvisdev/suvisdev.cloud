"use client"

import { useCallback, useEffect, useState } from "react"
import Image from "next/image"
import Link from "next/link"
import { BookOpen, ChevronDown, LayoutDashboard, LogOut, User } from "lucide-react"
import { AuthDialog } from "@/components/auth/auth-dialog"
import type { AuthFormsMode } from "@/app/login/auth-forms"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  logoutSession,
  getSuvisSession,
  SUVIS_SESSION_CHANGED_EVENT,
  type SuvisSession,
} from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

const navLinkClass =
  "text-xs font-medium text-neutral-600 transition-colors hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100 md:text-sm"

type AuthLoginButtonProps = {
  className?: string
}

export function AuthLoginButton({ className }: AuthLoginButtonProps) {
  const [open, setOpen] = useState(false)
  const [dialogTab, setDialogTab] = useState<AuthFormsMode>("login")
  const [session, setSession] = useState<SuvisSession | null>(null)

  const refreshSession = useCallback(() => {
    setSession(getSuvisSession())
  }, [])

  // 헤더에 있던 관리자 메뉴가 이 드롭다운으로 들어와서, 다른 탭 로그인·로그아웃·만료(SessionSync)도
  // 따라가야 한다 — 헤더가 듣던 이벤트를 그대로 구독한다.
  useEffect(() => {
    refreshSession()
    window.addEventListener(SUVIS_SESSION_CHANGED_EVENT, refreshSession)
    window.addEventListener("storage", refreshSession)
    return () => {
      window.removeEventListener(SUVIS_SESSION_CHANGED_EVENT, refreshSession)
      window.removeEventListener("storage", refreshSession)
    }
  }, [refreshSession, open])

  if (session) {
    const name = session.nickname ?? session.username
    const isAdmin = session.role === "admin"
    // 오른쪽 상단은 이름 하나만 — 마이페이지·관리자 메뉴·로그아웃은 눌러서 연다(2026-10-01 사용자)
    return (
      <DropdownMenu>
        <DropdownMenuTrigger
          className={cn(
            navLinkClass,
            "inline-flex shrink-0 items-center gap-1 rounded-md px-1.5 py-1 font-semibold text-neutral-800 outline-none hover:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-neutral-300 dark:text-neutral-200 dark:hover:bg-neutral-800",
            className
          )}
          aria-label={`${name} 메뉴`}
        >
          {/* 구글 프로필처럼 이름 앞에 Suvisdev 마크(2026-10-06) */}
          <Image src="/suvisdev-icon.svg" alt="" width={20} height={20} className="h-5 w-5 rounded-full" />
          <span className="max-w-[7rem] truncate md:max-w-[9rem]">{name}</span>
          <ChevronDown className="h-3.5 w-3.5 opacity-60" aria-hidden />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-44">
          <DropdownMenuLabel className="truncate">{name}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link href="/mypage">
              <User aria-hidden />
              마이페이지
            </Link>
          </DropdownMenuItem>
          {isAdmin && (
            <>
              <DropdownMenuItem asChild>
                <Link href="/admin">
                  <LayoutDashboard aria-hidden />
                  Admin
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/lesson">
                  <BookOpen aria-hidden />
                  LESSON
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild className="pl-8">
                <Link href="/titanic">타이타닉</Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild className="pl-8">
                <Link href="/titanic/data-collection">데이터 수집</Link>
              </DropdownMenuItem>
            </>
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onSelect={() => {
              void logoutSession()
              setSession(null)
            }}
          >
            <LogOut aria-hidden />
            로그아웃
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    )
  }

  const openDialog = (tab: AuthFormsMode) => {
    setDialogTab(tab)
    setOpen(true)
  }

  return (
    <>
      <div className={cn("flex shrink-0 items-center gap-2 sm:gap-2.5", className)}>
        <button
          type="button"
          onClick={() => openDialog("login")}
          className={cn(navLinkClass, "font-semibold text-neutral-800 dark:text-neutral-200")}
        >
          로그인
        </button>
        <button
          type="button"
          onClick={() => openDialog("signup")}
          className={cn(navLinkClass, "font-semibold text-neutral-800 dark:text-neutral-200")}
        >
          회원가입
        </button>
      </div>
      <AuthDialog open={open} onOpenChange={setOpen} defaultTab={dialogTab} />
    </>
  )
}
