"use client"

import { useCallback, useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { LogIn, LogOut } from "lucide-react"
import { AuthDialog } from "@/components/auth/auth-dialog"
import { fetchProfile } from "@/lib/profile-api"
import {
  clearSuvisSession,
  getSuvisSession,
  type SuvisSession,
} from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

/** mova 전용 로그인 버튼 — 공용 AuthDialog(viewer 로그인/회원가입)를 연다.
 *
 * 2026-07-22(beec23e)에 auth 게이트웨이(auth.suvisdev.cloud)로 직접 연결하는
 * 버전으로 바뀌었으나, EC2 `.env`에 `AUTH_GOOGLE_REDIRECT_URI` 등이 설정된
 * 적이 없어 실제로는 한 번도 동작하지 않았다(2026-08-11 확인,
 * apps/auth/_docs/auth_gateway_harness.md §5 "viewer→auth 실전환은 범위 밖"과
 * 일치). 게이트웨이가 완성될 때까지 beec23e 이전 방식(AuthDialog)으로
 * 되돌린다 — AuthDialog(`app/login/auth-forms.tsx`)가 OAuth(viewer/oauth
 * 경유)와 이메일 로그인/회원가입(viewer/login, viewer/signup)을 이미 전부
 * 제공하므로 기능 손실 없음. */

type MovaLoginButtonProps = {
  className?: string
  size?: "sm" | "md"
}

export function MovaLoginButton({ className, size = "sm" }: MovaLoginButtonProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [session, setSession] = useState<SuvisSession | null>(null)
  const [nickname, setNickname] = useState<string | null>(null)

  const refreshSession = useCallback(() => {
    setSession(getSuvisSession())
  }, [])

  useEffect(() => {
    refreshSession()
  }, [pathname, refreshSession, open])

  useEffect(() => {
    if (!session) {
      setNickname(null)
      return
    }
    let cancelled = false
    fetchProfile(session.id)
      .then((p) => {
        if (!cancelled) setNickname(p.nickname)
      })
      .catch(() => {
        if (!cancelled) setNickname(null)
      })
    return () => {
      cancelled = true
    }
  }, [session])

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
          title={nickname ?? session.username}
        >
          {nickname ?? session.username}
        </span>
        <button
          type="button"
          onClick={() => {
            clearSuvisSession()
            setSession(null)
          }}
          aria-label="로그아웃"
          className={cn(
            "inline-flex items-center justify-center gap-1 rounded-md border border-mova-border bg-mova-surface-2 text-mova-muted transition-colors hover:border-mova-accent/40 hover:bg-mova-accent-soft hover:text-mova-text",
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
          "inline-flex shrink-0 items-center justify-center gap-1.5 rounded-md border border-mova-accent/35 bg-mova-accent-soft font-medium text-mova-accent-bright transition-colors hover:border-mova-accent/55 hover:bg-mova-accent/25 hover:text-mova-text",
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
