"use client"

import { useCallback, useEffect, useState } from "react"
import { LogOut } from "lucide-react"
import { AuthDialog } from "@/components/auth/auth-dialog"
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
          title={session.username}
        >
          {session.username}
        </span>
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

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={cn(
          navLinkClass,
          "shrink-0 font-semibold text-neutral-800 dark:text-neutral-200",
          className,
        )}
      >
        로그인
      </button>
      <AuthDialog open={open} onOpenChange={setOpen} />
    </>
  )
}
