"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { LogOut, User } from "lucide-react"
import { AuthDialog } from "@/components/auth/auth-dialog"
import type { AuthFormsMode } from "@/app/login/auth-forms"
import {
  clearSuvisSession,
  getSuvisSession,
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

  useEffect(() => {
    refreshSession()
  }, [refreshSession, open])

  if (session) {
    return (
      <div className={cn("flex shrink-0 items-center gap-2", className)}>
        <span
          className="hidden max-w-[7rem] truncate text-xs font-medium text-neutral-700 dark:text-neutral-300 sm:inline md:max-w-[9rem] md:text-sm"
          title={session.nickname ?? session.username}
        >
          {session.nickname ?? session.username}
        </span>
        <Link
          href="/mypage"
          className={cn(
            navLinkClass,
            "inline-flex items-center gap-1 font-semibold text-neutral-800 dark:text-neutral-200",
          )}
          aria-label="마이페이지"
        >
          <User className="h-3.5 w-3.5" aria-hidden />
          <span className="hidden sm:inline">마이페이지</span>
        </Link>
        <button
          type="button"
          onClick={() => {
            clearSuvisSession()
            setSession(null)
          }}
          className={cn(
            navLinkClass,
            "inline-flex items-center gap-1 font-semibold text-neutral-800 dark:text-neutral-200",
          )}
          aria-label="로그아웃"
        >
          <LogOut className="h-3.5 w-3.5" aria-hidden />
          <span className="hidden sm:inline">로그아웃</span>
        </button>
      </div>
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
