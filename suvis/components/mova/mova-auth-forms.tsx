"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { ArrowLeft, Eye, EyeOff } from "lucide-react"
import { MovaLogo } from "@/components/mova/mova-logo"
import { OAuthButtons } from "@/components/auth/oauth-buttons"
import type { FormStatus} from "@/lib/form-status";
import { initialFormStatus, isSuccessMessage } from "@/lib/form-status"
import { rememberPostLoginPath, saveSuvisSession } from "@/lib/suvis-session"
import { cn } from "@/lib/utils"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

type LoginFormProps = { username: string; password: string }
type SignupFormProps = { username: string; password: string; nickname: string; email: string }

// 로그인·회원가입은 `/api/auth/login`·`/api/auth/signup` BFF 프록시로 나간다 — 토큰은 서버가 쿠키로 심는다.

const inputClass =
  "h-11 w-full rounded-lg border border-mova-border bg-mova-surface-2 px-4 text-sm text-mova-text placeholder:text-neutral-500 outline-none transition focus:border-mova-accent/50 focus:ring-1 focus:ring-mova-accent-soft"

export function MovaAuthForms() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const redirect = searchParams.get("redirect")?.trim() || "/mova/main"
  const [tab, setTab] = useState<"login" | "signup">("login")
  const [showPassword, setShowPassword] = useState(false)
  const [login, setLogin] = useState<FormStatus>(initialFormStatus)
  const [signup, setSignup] = useState<FormStatus>(initialFormStatus)

  // 소셜 로그인도 끝나면 mova의 원래 가려던 곳으로 돌아오게 한다(기본은 사이트 홈이라 mova를 벗어났다).
  useEffect(() => {
    rememberPostLoginPath(redirect.startsWith("/mova") ? redirect : "/mova/main")
  }, [redirect])

  const patchLogin = (patch: Partial<FormStatus>) => setLogin((prev) => ({ ...prev, ...patch }))
  const patchSignup = (patch: Partial<FormStatus>) => setSignup((prev) => ({ ...prev, ...patch }))

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const formProps = Object.fromEntries(formData.entries()) as LoginFormProps

    patchLogin({ message: null })
    const errors: Record<string, string> = {}
    if (!formProps.username.trim()) errors.username = "아이디를 입력해주세요"
    if (!formProps.password) errors.password = "비밀번호를 입력해주세요"
    if (Object.keys(errors).length) {
      patchLogin({ errors })
      return
    }

    patchLogin({ errors: {}, submitting: true })
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formProps.username.trim(),
          password: formProps.password,
        }),
      })
      let body: { id?: number; username?: string; detail?: unknown }
      try {
        body = (await res.json()) as { id?: number; username?: string; detail?: unknown }
      } catch {
        patchLogin({ message: "서버 응답을 읽을 수 없습니다." })
        return
      }
      if (!res.ok || typeof body.id !== "number") {
        patchLogin({
          message: safeApiErrorMessage(
            body.detail,
            res.status === 401
              ? "아이디 또는 비밀번호가 올바르지 않습니다."
              : "로그인에 실패했습니다.",
            res.status,
          ),
        })
        return
      }
      saveSuvisSession({ id: body.id, username: body.username || `user-${body.id}` })
      router.replace(redirect.startsWith("/mova") ? redirect : "/mova/main")
    } catch {
      patchLogin({ message: "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요." })
    } finally {
      patchLogin({ submitting: false })
    }
  }

  const handleSignup = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const formProps = Object.fromEntries(formData.entries()) as SignupFormProps

    patchSignup({ message: null })
    const errors: Record<string, string> = {}
    if (!formProps.username.trim()) errors.username = "아이디를 입력해주세요"
    if (!formProps.password || formProps.password.length < 8) errors.password = "비밀번호는 8자 이상이어야 합니다"
    if (!formProps.nickname.trim()) errors.nickname = "닉네임을 입력해주세요"
    if (!formProps.email.trim()) errors.email = "이메일을 입력해주세요"
    if (Object.keys(errors).length) {
      patchSignup({ errors })
      return
    }

    patchSignup({ errors: {}, submitting: true })
    try {
      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: formProps.email.trim(),
          password: formProps.password,
          username: formProps.username.trim() || undefined,
        }),
      })
      let body: { id?: number; username?: string; detail?: unknown }
      try {
        body = (await res.json()) as { id?: number; username?: string; detail?: unknown }
      } catch {
        patchSignup({ message: "서버 응답을 읽을 수 없습니다." })
        return
      }
      if (!res.ok || typeof body.id !== "number") {
        patchSignup({
          message: safeApiErrorMessage(
            body.detail,
            res.status === 409 ? "이미 가입된 이메일입니다." : "회원가입에 실패했습니다.",
            res.status,
          ),
        })
        return
      }
      // 회원가입 = 세션 발급 완료(BFF가 쿠키 세팅). 바로 진입.
      saveSuvisSession({
        id: body.id,
        username: body.username || formProps.nickname.trim() || `user-${body.id}`,
      })
      router.replace(redirect.startsWith("/mova") ? redirect : "/mova/main")
    } catch {
      patchSignup({ message: "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요." })
    } finally {
      patchSignup({ submitting: false })
    }
  }

  return (
    <div className="mova-cinema-bg relative flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <div className="relative z-10 w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <MovaLogo size="lg" href="/mova" />
        </div>

        <div className="overflow-hidden rounded-2xl border border-mova-border bg-mova-surface shadow-[0_12px_48px_rgba(0,0,0,0.5)]">
          <div className="flex border-b border-mova-border">
            {(["login", "signup"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={cn(
                  "flex-1 py-4 text-sm font-semibold transition-colors",
                  tab === t
                    ? "border-b-2 border-mova-accent text-mova-text"
                    : "text-neutral-500 hover:text-mova-text",
                )}
              >
                {t === "login" ? "로그인" : "회원가입"}
              </button>
            ))}
          </div>

          {/* 소셜 로그인 — OAuth 사용자의 재로그인 경로 확보 (2026-08-13).
              /viewer/oauth/{provider}/login으로 이동 → /oauth/callback에서
              saveSuvisSession 완료. 아이디/비번 폼과 동일 세션을 씀. */}
          <div className="px-6 pt-6">
            <OAuthButtons />
            <div className="my-5 flex items-center gap-3">
              <div className="h-px flex-1 bg-mova-border" />
              <span className="text-[11px] text-neutral-500">또는</span>
              <div className="h-px flex-1 bg-mova-border" />
            </div>
          </div>

          {tab === "login" ? (
            <form onSubmit={handleLogin} className="space-y-4 px-6 pb-6">
              <div className="space-y-2">
                <label htmlFor="mova-login-username" className="text-sm text-neutral-400">아이디</label>
                <input id="mova-login-username" name="username" type="text" autoComplete="username" placeholder="아이디" className={inputClass} />
                {login.errors.username && <p className="text-xs text-red-400">{login.errors.username}</p>}
              </div>
              <div className="space-y-2">
                <label htmlFor="mova-login-password" className="text-sm text-neutral-400">비밀번호</label>
                <div className="relative">
                  <input id="mova-login-password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="비밀번호" className={cn(inputClass, "pr-11")} />
                  <button type="button" onClick={() => setShowPassword((v) => !v)} className="absolute top-1/2 right-3 -translate-y-1/2 text-neutral-500 hover:text-neutral-300" aria-label={showPassword ? "비밀번호 숨기기" : "비밀번호 보기"}>
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {login.errors.password && <p className="text-xs text-red-400">{login.errors.password}</p>}
              </div>
              {login.message && (
                <p className={cn("text-center text-sm", isSuccessMessage(login.message) ? "text-emerald-400" : "text-red-400")}>
                  {login.message}
                </p>
              )}
              <button type="submit" disabled={login.submitting} className="h-11 w-full rounded-lg bg-mova-accent text-sm font-semibold text-white shadow-lg shadow-mova-accent-soft transition hover:brightness-110 disabled:opacity-50">
                {login.submitting ? "로그인 중…" : "로그인"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleSignup} className="space-y-4 px-6 pb-6">
              <div className="space-y-2">
                <label htmlFor="mova-signup-username" className="text-sm text-neutral-400">아이디</label>
                <input id="mova-signup-username" name="username" type="text" autoComplete="username" placeholder="아이디" className={inputClass} />
                {signup.errors.username && <p className="text-xs text-red-400">{signup.errors.username}</p>}
              </div>
              <div className="space-y-2">
                <label htmlFor="mova-signup-password" className="text-sm text-neutral-400">비밀번호</label>
                <div className="relative">
                  <input id="mova-signup-password" name="password" type={showPassword ? "text" : "password"} autoComplete="new-password" placeholder="비밀번호 (8자 이상)" className={cn(inputClass, "pr-11")} />
                  <button type="button" onClick={() => setShowPassword((v) => !v)} className="absolute top-1/2 right-3 -translate-y-1/2 text-neutral-500 hover:text-neutral-300" aria-label={showPassword ? "비밀번호 숨기기" : "비밀번호 보기"}>
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {signup.errors.password && <p className="text-xs text-red-400">{signup.errors.password}</p>}
              </div>
              <div className="space-y-2">
                <label htmlFor="mova-signup-nickname" className="text-sm text-neutral-400">닉네임</label>
                <input id="mova-signup-nickname" name="nickname" type="text" placeholder="닉네임" className={inputClass} />
                {signup.errors.nickname && <p className="text-xs text-red-400">{signup.errors.nickname}</p>}
              </div>
              <div className="space-y-2">
                <label htmlFor="mova-signup-email" className="text-sm text-neutral-400">이메일</label>
                <input id="mova-signup-email" name="email" type="email" autoComplete="email" placeholder="이메일" className={inputClass} />
                {signup.errors.email && <p className="text-xs text-red-400">{signup.errors.email}</p>}
              </div>
              {signup.message && (
                <p className={cn("text-center text-sm", isSuccessMessage(signup.message) ? "text-emerald-400" : "text-red-400")}>
                  {signup.message}
                </p>
              )}
              <button type="submit" disabled={signup.submitting} className="h-11 w-full rounded-lg bg-mova-accent text-sm font-semibold text-white shadow-lg shadow-mova-accent-soft transition hover:brightness-110 disabled:opacity-50">
                {signup.submitting ? "가입 중…" : "회원가입"}
              </button>
            </form>
          )}
        </div>

        <p className="mt-6 text-center">
          <Link href="/mova" className="inline-flex items-center gap-1.5 text-sm text-neutral-500 transition-colors hover:text-mova-text">
            <ArrowLeft className="h-3.5 w-3.5" />
            Mova로 돌아가기
          </Link>
        </p>
      </div>
    </div>
  )
}
