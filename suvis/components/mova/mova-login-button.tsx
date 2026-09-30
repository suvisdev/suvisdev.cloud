"use client"

import { useCallback, useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { LogIn, LogOut } from "lucide-react"
import { AuthDialog } from "@/components/auth/auth-dialog"
import { fetchProfile } from "@/lib/profile-api"
import {
  logoutSession,
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

// 새로고침 후에도 첫 렌더부터 닉네임을 보여주기 위한 localStorage 캐시.
// (이전의 모듈 레벨 캐시는 메모리라 새로고침 시 username이 먼저 노출됐다.)
function readCachedNickname(userId: number): string | null {
  try {
    return localStorage.getItem(`mova-nickname:${userId}`)
  } catch {
    return null
  }
}

function writeCachedNickname(userId: number, nickname: string) {
  try {
    localStorage.setItem(`mova-nickname:${userId}`, nickname)
  } catch {
    // 저장 실패는 무시 — 다음 fetch가 다시 채운다.
  }
}

export function MovaLoginButton({ className, size = "sm" }: MovaLoginButtonProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  // SSR 마크업과 hydration 첫 렌더를 일치시키기 위해 세션은 effect에서 읽는다.
  // hydrated 전에는 자리만 잡는 placeholder를 그려 "로그인 → 닉네임" 플래시를 막는다.
  const [hydrated, setHydrated] = useState(false)
  const [session, setSession] = useState<SuvisSession | null>(null)
  const [nickname, setNickname] = useState<string | null>(null)

  const refreshSession = useCallback(() => {
    const s = getSuvisSession()
    setSession(s)
    // 세션과 같은 렌더 커밋에 캐시 닉네임을 함께 넣어 username 노출 프레임을 없앤다.
    setNickname(s ? readCachedNickname(s.id) : null)
  }, [])

  useEffect(() => {
    refreshSession()
    setHydrated(true)
  }, [pathname, refreshSession, open])

  useEffect(() => {
    if (!session) return
    let cancelled = false
    fetchProfile(session.id)
      .then((p) => {
        writeCachedNickname(session.id, p.nickname)
        if (!cancelled) setNickname(p.nickname)
      })
      .catch(() => {
        // 실패 시 캐시/username 표시 유지
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

  if (!hydrated) {
    // 세션 확인 전 자리 표시 — 로그인 버튼과 같은 높이의 빈 박스.
    return <div className={cn("h-8 w-8 shrink-0 sm:w-20", className)} aria-hidden />
  }

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
            void logoutSession()
            setSession(null)
            setNickname(null)
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
