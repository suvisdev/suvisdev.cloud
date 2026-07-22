"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { LogIn, LogOut } from "lucide-react"
import {
  getSuvisSession,
  clearSuvisSession,
  saveSuvisSession,
  type SuvisSession,
} from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

/** mova 전용 로그인 버튼 — auth 게이트웨이(auth.suvisdev.cloud)로 직접 리다이렉트.
 * 기존에 viewer 로그인 API(공용 AuthDialog)를 열던 로직을 대체한다.
 * components/auth/auth-login-button.tsx, oauth-buttons.tsx 등 공용 파일은
 * 무관 — 이 파일 하나만 바뀐다.
 *
 * code 파라미터는 useSearchParams()가 아니라 window.location.search로 직접
 * 읽는다 — useSearchParams()는 Suspense 경계를 강제해서, 정적 셸에서는
 * fallback만 보이고 실제 버튼은 하이드레이션 후에야 나타나는 회귀가 있었다. */

type MovaLoginButtonProps = {
  className?: string
  size?: "sm" | "md"
}

type OAuthProvider = "google" | "kakao" | "naver"

const AUTH_BASE = "https://auth.suvisdev.cloud"
const MOVA_AUD = "suvis-mova"
const MOVA_RETURN_TO = "/mova"
const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://127.0.0.1:8000"

const PROVIDERS: { id: OAuthProvider; label: string; className: string }[] = [
  {
    id: "google",
    label: "Google로 계속하기",
    className: "border border-neutral-300 bg-white text-neutral-800 hover:bg-neutral-50",
  },
  {
    id: "kakao",
    label: "카카오로 계속하기",
    className: "border border-transparent bg-[#FEE500] text-[#191919] hover:bg-[#f5dc00]",
  },
  {
    id: "naver",
    label: "네이버로 계속하기",
    className: "border border-transparent bg-[#03C75A] text-white hover:bg-[#02b350]",
  },
]

function startOAuthLogin(provider: OAuthProvider) {
  const params = new URLSearchParams({ aud: MOVA_AUD, return_to: MOVA_RETURN_TO })
  window.location.href = `${AUTH_BASE}/auth/login/${provider}?${params.toString()}`
}

// 헤더가 MovaLoginButton을 두 번(모바일/데스크톱) 렌더링하므로, 같은 handoff
// code를 두 인스턴스가 동시에 소비 시도하지 않도록 모듈 스코프에서 한 번만 처리.
let _processedHandoffCode: string | null = null

export function MovaLoginButton({ className, size = "sm" }: MovaLoginButtonProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [menuOpen, setMenuOpen] = useState(false)
  const [session, setSession] = useState<SuvisSession | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  const refreshSession = useCallback(() => {
    setSession(getSuvisSession())
  }, [])

  useEffect(() => {
    refreshSession()
  }, [pathname, refreshSession])

  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get("code")
    if (!code || code === _processedHandoffCode) return
    _processedHandoffCode = code

    let cancelled = false

    async function completeOAuthLogin() {
      try {
        const exchangeRes = await fetch(`${AUTH_BASE}/auth/exchange`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code }),
        })
        if (!exchangeRes.ok) return
        const { access_token: accessToken } = (await exchangeRes.json()) as {
          access_token: string
        }
        if (cancelled) return

        const whoamiRes = await fetch(`${API_BASE}/mova/whoami`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        })
        if (!whoamiRes.ok) return
        const whoami = (await whoamiRes.json()) as { sub: string; username: string }
        if (cancelled) return

        saveSuvisSession({
          id: Number(whoami.sub),
          username: whoami.username || `user-${whoami.sub}`,
        })
        refreshSession()
      } finally {
        if (!cancelled) {
          // handoff code는 1회용이라 재사용 불가 — 주소창에서도 정리
          router.replace(pathname)
        }
      }
    }

    void completeOAuthLogin()
    return () => {
      cancelled = true
    }
  }, [pathname, router, refreshSession])

  useEffect(() => {
    if (!menuOpen) return
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [menuOpen])

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
    <div className={cn("relative shrink-0", className)} ref={menuRef}>
      <button
        type="button"
        onClick={() => setMenuOpen((v) => !v)}
        aria-label="로그인"
        className={cn(
          "inline-flex shrink-0 items-center justify-center gap-1.5 rounded-md border border-[var(--mova-accent)]/35 bg-[var(--mova-accent-soft)] font-medium text-[var(--mova-accent-bright)] transition-colors hover:border-[var(--mova-accent)]/55 hover:bg-[var(--mova-accent)]/25 hover:text-[var(--mova-text)]",
          size === "sm" ? "h-8 min-w-8 px-2 text-xs sm:min-w-0 sm:px-3 sm:text-sm" : "h-9 px-4 text-sm",
        )}
      >
        <LogIn className="h-3.5 w-3.5 shrink-0" />
        <span className="hidden sm:inline">로그인</span>
      </button>
      {menuOpen && (
        <div className="absolute right-0 top-full z-50 mt-2 w-56 space-y-2 rounded-xl border border-[var(--mova-border)] bg-[var(--mova-surface)] p-3 shadow-lg shadow-black/20">
          {PROVIDERS.map(({ id, label, className: providerClassName }) => (
            <button
              key={id}
              type="button"
              onClick={() => startOAuthLogin(id)}
              className={cn(
                "flex w-full items-center justify-center rounded-lg px-3 py-2 text-xs font-semibold shadow-sm transition-colors",
                providerClassName,
              )}
            >
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
