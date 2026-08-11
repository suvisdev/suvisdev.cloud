"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { usePathname } from "next/navigation"
import { LogIn, LogOut } from "lucide-react"
import {
  getSuvisSession,
  clearSuvisSession,
  saveSuvisSession,
  type SuvisSession,
} from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

/** mova 전용 로그인 버튼.
 *
 * OAuth(Google/Kakao/Naver)는 apps/viewer의 기존 로그인 플로우
 * (`components/auth/oauth-buttons.tsx`와 동일)를 그대로 쓴다 — auth
 * 게이트웨이(auth.suvisdev.cloud)로 연결했던 이전 버전은 EC2 `.env`에
 * `AUTH_GOOGLE_REDIRECT_URI` 등이 설정된 적이 없어 503을 내며 실제로는
 * 한 번도 동작하지 않았다(2026-08-11 확인, apps/auth/_docs/auth_gateway_harness.md
 * §5 "viewer→auth 실전환은 범위 밖"과 일치). 이메일 로그인/회원가입만 계속
 * auth 게이트웨이(`/auth/login`, `/auth/signup`, 비밀번호 방식)를 쓴다 —
 * 이쪽은 redirect_uri와 무관하게 별도로 동작 확인됨. */

type MovaLoginButtonProps = {
  className?: string
  size?: "sm" | "md"
}

type OAuthProvider = "google" | "kakao" | "naver"
type EmailFormMode = "login" | "signup"

const AUTH_BASE = "https://auth.suvisdev.cloud"
const MOVA_AUD = "suvis-mova"
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

const inputClass =
  "h-9 w-full rounded-md border border-mova-border bg-mova-surface-2 px-2.5 text-xs text-mova-text placeholder:text-neutral-500 outline-none transition focus:border-mova-accent/50"

function startOAuthLogin(provider: OAuthProvider) {
  window.location.href = `${API_BASE}/viewer/oauth/${provider}/login`
}

async function fetchWhoamiUsername(accessToken: string): Promise<{ sub: string; username: string }> {
  const res = await fetch(`${API_BASE}/mova/whoami`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) throw new Error("사용자 정보를 불러오지 못했습니다.")
  return (await res.json()) as { sub: string; username: string }
}

export function MovaLoginButton({ className, size = "sm" }: MovaLoginButtonProps) {
  const pathname = usePathname()
  const [menuOpen, setMenuOpen] = useState(false)
  const [session, setSession] = useState<SuvisSession | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  const [emailFormOpen, setEmailFormOpen] = useState(false)
  const [emailFormMode, setEmailFormMode] = useState<EmailFormMode>("login")
  const [emailFormError, setEmailFormError] = useState<string | null>(null)
  const [emailFormSubmitting, setEmailFormSubmitting] = useState(false)

  const refreshSession = useCallback(() => {
    setSession(getSuvisSession())
  }, [])

  useEffect(() => {
    refreshSession()
  }, [pathname, refreshSession])

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

  const closeMenu = useCallback(() => {
    setMenuOpen(false)
    setEmailFormOpen(false)
    setEmailFormError(null)
  }, [])

  const handleEmailSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    setEmailFormError(null)
    setEmailFormSubmitting(true)
    try {
      const endpoint = emailFormMode === "login" ? "/auth/login" : "/auth/signup"
      const payload =
        emailFormMode === "login"
          ? {
              username: String(formData.get("username") ?? ""),
              password: String(formData.get("password") ?? ""),
              aud: MOVA_AUD,
            }
          : {
              email: String(formData.get("email") ?? ""),
              password: String(formData.get("password") ?? ""),
              username: String(formData.get("username") ?? "") || undefined,
              aud: MOVA_AUD,
            }

      const res = await fetch(`${AUTH_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      const body = (await res.json()) as { access_token?: string; detail?: string }
      if (!res.ok) {
        setEmailFormError(
          res.status === 409
            ? "이미 가입된 이메일입니다."
            : res.status === 401
              ? "아이디 또는 비밀번호가 올바르지 않습니다."
              : (body.detail ?? "요청을 처리하지 못했습니다."),
        )
        return
      }

      const whoami = await fetchWhoamiUsername(body.access_token as string)
      saveSuvisSession({
        id: Number(whoami.sub),
        username: whoami.username || `user-${whoami.sub}`,
      })
      refreshSession()
      closeMenu()
    } catch {
      setEmailFormError("서버에 연결할 수 없습니다.")
    } finally {
      setEmailFormSubmitting(false)
    }
  }

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
    <div className={cn("relative shrink-0", className)} ref={menuRef}>
      <button
        type="button"
        onClick={() => setMenuOpen((v) => !v)}
        aria-label="로그인"
        className={cn(
          "inline-flex shrink-0 items-center justify-center gap-1.5 rounded-md border border-mova-accent/35 bg-mova-accent-soft font-medium text-mova-accent-bright transition-colors hover:border-mova-accent/55 hover:bg-mova-accent/25 hover:text-mova-text",
          size === "sm" ? "h-8 min-w-8 px-2 text-xs sm:min-w-0 sm:px-3 sm:text-sm" : "h-9 px-4 text-sm",
        )}
      >
        <LogIn className="h-3.5 w-3.5 shrink-0" />
        <span className="hidden sm:inline">로그인</span>
      </button>
      {menuOpen && (
        <div className="absolute right-0 top-full z-50 mt-2 w-64 space-y-2 rounded-xl border border-mova-border bg-mova-surface p-3 shadow-lg shadow-black/20">
          {!emailFormOpen && (
            <>
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
              <div className="flex items-center gap-2 py-0.5">
                <div className="h-px flex-1 bg-mova-border" />
                <span className="text-[10px] text-neutral-500">또는</span>
                <div className="h-px flex-1 bg-mova-border" />
              </div>
              <button
                type="button"
                onClick={() => {
                  setEmailFormOpen(true)
                  setEmailFormError(null)
                }}
                className="flex w-full items-center justify-center rounded-lg border border-mova-border bg-mova-surface-2 px-3 py-2 text-xs font-semibold text-mova-text transition-colors hover:bg-mova-accent-soft"
              >
                이메일로 가입/로그인
              </button>
            </>
          )}

          {emailFormOpen && (
            <div className="space-y-2.5">
              <div className="flex gap-1 rounded-lg bg-mova-surface-2 p-0.5">
                {(["login", "signup"] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => {
                      setEmailFormMode(mode)
                      setEmailFormError(null)
                    }}
                    className={cn(
                      "flex-1 rounded-md py-1.5 text-xs font-semibold transition-colors",
                      emailFormMode === mode
                        ? "bg-mova-accent text-white"
                        : "text-neutral-400 hover:text-mova-text",
                    )}
                  >
                    {mode === "login" ? "로그인" : "회원가입"}
                  </button>
                ))}
              </div>

              <form onSubmit={handleEmailSubmit} className="space-y-2">
                {emailFormMode === "login" ? (
                  <input
                    name="username"
                    type="text"
                    placeholder="아이디"
                    autoComplete="username"
                    className={inputClass}
                  />
                ) : (
                  <>
                    <input
                      name="email"
                      type="email"
                      placeholder="이메일"
                      autoComplete="email"
                      className={inputClass}
                    />
                    <input
                      name="username"
                      type="text"
                      placeholder="아이디(선택, 비우면 이메일 앞부분 사용)"
                      autoComplete="username"
                      className={inputClass}
                    />
                  </>
                )}
                <input
                  name="password"
                  type="password"
                  placeholder={emailFormMode === "login" ? "비밀번호" : "비밀번호 (8자 이상)"}
                  autoComplete={emailFormMode === "login" ? "current-password" : "new-password"}
                  className={inputClass}
                />
                {emailFormError && <p className="text-[11px] text-red-400">{emailFormError}</p>}
                <button
                  type="submit"
                  disabled={emailFormSubmitting}
                  className="h-9 w-full rounded-md bg-mova-accent text-xs font-semibold text-white transition hover:brightness-110 disabled:opacity-50"
                >
                  {emailFormSubmitting
                    ? "처리 중..."
                    : emailFormMode === "login"
                      ? "로그인"
                      : "가입하기"}
                </button>
              </form>

              <button
                type="button"
                onClick={() => {
                  setEmailFormOpen(false)
                  setEmailFormError(null)
                }}
                className="w-full text-center text-[11px] text-neutral-500 hover:text-mova-text"
              >
                ← 다른 방법으로 로그인
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
