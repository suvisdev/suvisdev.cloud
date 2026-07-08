"use client"

import { useCallback, useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { LogIn, LogOut } from "lucide-react"
import { AuthDialog } from "@/components/auth/auth-dialog"
import {
  clearSuvisSession,
  getSuvisSession,
  type SuvisSession,
} from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

type MovaLoginButtonProps = {
  className?: string
  size?: "sm" | "md"
}

export function MovaLoginButton({ className, size = "sm" }: MovaLoginButtonProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [session, setSession] = useState<SuvisSession | null>(null)

  const refreshSession = useCallback(() => {
    setSession(getSuvisSession())
  }, [])

  useEffect(() => {
    refreshSession()
  }, [pathname, refreshSession, open])

  const onAuthSuccess = useCallback(() => {
    setOpen(false)
    refreshSession()
    router.refresh()
  }, [refreshSession, router])

  if (session) {
    return (
      <div className={cn("flex shrink-0 items-center gap-1.5 sm:gap-2", className)}>
        <span
          className={cn(
            "hidden max-w-[6rem] truncate text-neutral-300 sm:inline sm:max-w-[9rem]",
            size === "sm" ? "text-xs sm:text-sm" : "text-sm",
          )}
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
          aria-label="로그아웃"
          className={cn(
            "inline-flex items-center justify-center gap-1 rounded-md border border-[var(--mova-border)] bg-[var(--mova-surface-2)] text-[var(--mova-muted)] transition-colors hover:border-[var(--mova-accent)]/40 hover:bg-[var(--mova-accent-soft)] hover:text-[var(--mova-text)]",
            size === "sm" ? "h-8 min-w-8 px-2 text-xs sm:min-w-0 sm:px-2.5" : "h-9 px-3 text-sm",
          )}
        >
          <LogOut className="h-3.5 w-3.5 shrink-0" />
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
        aria-label="로그인"
        className={cn(
          "inline-flex shrink-0 items-center justify-center gap-1.5 rounded-md border border-[var(--mova-accent)]/35 bg-[var(--mova-accent-soft)] font-medium text-[var(--mova-accent-bright)] transition-colors hover:border-[var(--mova-accent)]/55 hover:bg-[var(--mova-accent)]/25 hover:text-[var(--mova-text)]",
          size === "sm" ? "h-8 min-w-8 px-2 text-xs sm:min-w-0 sm:px-3 sm:text-sm" : "h-9 px-4 text-sm",
          className,
        )}
      >
        <LogIn className="h-3.5 w-3.5 shrink-0" />
        <span className="hidden sm:inline">로그인</span>
      </button>
      <AuthDialog
        open={open}
        onOpenChange={setOpen}
        defaultTab="login"
        onAuthSuccess={onAuthSuccess}
      />
    </>
  )
}
