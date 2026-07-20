"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { ArrowLeft, Eye, EyeOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FormStatus, initialFormStatus, isSuccessMessage } from "@/lib/form-status"
import { cn } from "@/lib/utils"
import { safeApiErrorMessage } from "@/lib/user-facing-error"
import { saveSuvisSession } from "@/lib/suvis-session"
import { OAuthButtons, type OAuthProvider } from "@/components/auth/oauth-buttons"

const OAUTH_PROVIDER_LABEL: Record<OAuthProvider, string> = {
  google: "Google",
  naver: "네이버",
  kakao: "카카오",
  instagram: "Instagram",
}

export type AuthFormsMode = "login" | "signup"

type AuthFormsProps = {
  mode?: AuthFormsMode
  /** page: 전체 페이지 · embedded: 헤더 팝업 등 */
  variant?: "page" | "embedded"
  onAuthSuccess?: () => void
}

type UiState = {
  tab: AuthFormsMode
  showPassword: boolean
}

type LoginFormProps = {
  username: string
  password: string
}

type SignupFormProps = {
  username: string
  password: string
  confirmPassword: string
  nickname: string
  email: string
  gender: string
  age_group: string
  birth_year: string
}

type AuthApiResponse = { message?: string; id?: number; username?: string }
type AuthApiErrorBody = { detail?: string | unknown }

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://127.0.0.1:8000"

const tabListClass =
  "grid h-10 w-full grid-cols-2 rounded-xl border border-neutral-300 bg-neutral-100/80 p-1"
const tabTriggerClass =
  "rounded-lg border-transparent text-sm text-neutral-600 shadow-none focus-visible:ring-0 focus-visible:outline-none data-[state=active]:border-transparent data-[state=active]:bg-white data-[state=active]:text-neutral-900 data-[state=active]:shadow-sm"

function parseApiDetail(body: AuthApiErrorBody, status: number, notFound: string, failed: string) {
  const fallback = status === 404 ? notFound : failed
  return safeApiErrorMessage(body.detail, fallback, status)
}

export function AuthForms({
  mode = "login",
  variant = "page",
  onAuthSuccess,
}: AuthFormsProps) {
  const router = useRouter()
  const [ui, setUi] = useState<UiState>({ tab: mode, showPassword: false })
  const [login, setLogin] = useState<FormStatus>(initialFormStatus)
  const [signup, setSignup] = useState<FormStatus>(initialFormStatus)
  const [oauthNotice, setOauthNotice] = useState<string | null>(null)

  const handleOAuthSelect = (provider: OAuthProvider) => {
    setOauthNotice(`${OAUTH_PROVIDER_LABEL[provider]} 로그인은 준비 중입니다.`)
  }

  const patchLogin = (patch: Partial<FormStatus>) =>
    setLogin((prev) => ({ ...prev, ...patch }))
  const patchSignup = (patch: Partial<FormStatus>) =>
    setSignup((prev) => ({ ...prev, ...patch }))

  const validateLogin = (formProps: LoginFormProps) => {
    const errors: Record<string, string> = {}
    if (!formProps.username.trim()) errors.username = "아이디를 입력해주세요"
    if (!formProps.password) errors.password = "비밀번호를 입력해주세요"
    return errors
  }

  const validateSignup = (formProps: SignupFormProps) => {
    const errors: Record<string, string> = {}
    if (!formProps.username.trim()) errors.username = "아이디를 입력해주세요"
    else if (formProps.username.length < 4) errors.username = "아이디는 4자 이상이어야 합니다"
    if (!formProps.password) errors.password = "비밀번호를 입력해주세요"
    else if (formProps.password.length < 6) errors.password = "비밀번호는 6자 이상이어야 합니다"
    if (formProps.password !== formProps.confirmPassword) {
      errors.confirmPassword = "비밀번호가 일치하지 않습니다"
    }
    if (!formProps.nickname.trim()) errors.nickname = "닉네임을 입력해주세요"
    if (!formProps.email.trim()) errors.email = "이메일을 입력해주세요"
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formProps.email.trim())) {
      errors.email = "올바른 이메일 형식이 아닙니다"
    }
    return errors
  }

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const formProps = Object.fromEntries(formData.entries()) as LoginFormProps

    patchLogin({ message: null })
    const errors = validateLogin(formProps)
    if (Object.keys(errors).length) {
      patchLogin({ errors })
      return
    }

    patchLogin({ errors: {}, submitting: true })
    try {
      const res = await fetch(`${API_BASE}/friday13th/login/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formProps.username.trim(),
          password: formProps.password,
        }),
      })
      let body: AuthApiResponse & AuthApiErrorBody
      try {
        body = (await res.json()) as AuthApiResponse & AuthApiErrorBody
      } catch {
        patchLogin({ message: "서버 응답을 읽을 수 없습니다." })
        return
      }
      if (!res.ok) {
        patchLogin({
          message: parseApiDetail(
            body,
            res.status,
            "로그인 API를 찾을 수 없습니다. 백엔드 경로를 확인해 주세요.",
            "로그인에 실패했습니다.",
          ),
        })
        return
      }
      if (typeof body.id === "number" && body.username) {
        saveSuvisSession({ id: body.id, username: body.username })
      }
      patchLogin({ message: body.message ?? "로그인에 성공했습니다." })
      onAuthSuccess?.()
      if (variant === "page") {
        router.refresh()
      }
    } catch {
      patchLogin({
        message: "백엔드에 연결할 수 없습니다. 서버가 실행 중인지 확인해 주세요.",
      })
    } finally {
      patchLogin({ submitting: false })
    }
  }

  const handleSignup = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const formProps = Object.fromEntries(formData.entries()) as SignupFormProps

    patchSignup({ message: null })
    const errors = validateSignup(formProps)
    if (Object.keys(errors).length) {
      patchSignup({ errors })
      return
    }

    patchSignup({ errors: {}, submitting: true })
    try {
      const res = await fetch(`${API_BASE}/friday13th/signup/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formProps.username.trim(),
          password: formProps.password,
          nickname: formProps.nickname.trim(),
          email: formProps.email.trim(),
          gender: formProps.gender || "undisclosed",
          age_group: formProps.age_group || "undisclosed",
          birth_year: formProps.birth_year
            ? Number.parseInt(formProps.birth_year, 10)
            : null,
        }),
      })
      let body: AuthApiResponse & AuthApiErrorBody
      try {
        body = (await res.json()) as AuthApiResponse & AuthApiErrorBody
      } catch {
        patchSignup({ message: "서버 응답을 읽을 수 없습니다." })
        return
      }
      if (!res.ok) {
        patchSignup({
          message: parseApiDetail(
            body,
            res.status,
            "회원가입 API를 찾을 수 없습니다. 백엔드 경로를 확인해 주세요.",
            "회원가입에 실패했습니다.",
          ),
        })
        return
      }
      patchSignup({ message: body.message ?? "회원가입이 완료되었습니다. 로그인해 주세요." })
      setUi((prev) => ({ ...prev, tab: "login" }))
    } catch {
      patchSignup({
        message: "백엔드에 연결할 수 없습니다. 서버가 실행 중인지 확인해 주세요.",
      })
    } finally {
      patchSignup({ submitting: false })
    }
  }

  const inputClass =
    "border-neutral-300 bg-white text-neutral-900 placeholder:text-neutral-400 focus-visible:ring-neutral-400/40"

  const passwordToggle = (
    <button
      type="button"
      onClick={() => setUi((prev) => ({ ...prev, showPassword: !prev.showPassword }))}
      className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 transition-colors hover:text-neutral-700"
      aria-label={ui.showPassword ? "비밀번호 숨기기" : "비밀번호 보기"}
    >
      {ui.showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
    </button>
  )

  const card = (
    <Card
      className={
        variant === "page"
          ? "w-full max-w-md rounded-3xl border-neutral-300/80 bg-white shadow-lg shadow-neutral-900/5"
          : "w-full gap-4 border-0 bg-white py-6 shadow-none"
      }
    >
      <CardHeader className="space-y-1 pb-2 text-center">
        <CardTitle className="text-2xl font-bold tracking-tight text-neutral-900">
          Suvis<span className="font-extrabold">dev</span>
        </CardTitle>
        <CardDescription className="text-neutral-500">
          로그인하거나 새 계정을 만드세요
        </CardDescription>
      </CardHeader>
      <CardContent>
          <OAuthButtons onSelect={handleOAuthSelect} />
          {oauthNotice && (
            <p className="mt-2.5 text-center text-xs text-neutral-500">{oauthNotice}</p>
          )}
          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-neutral-200" />
            <span className="text-xs text-neutral-400">또는</span>
            <div className="h-px flex-1 bg-neutral-200" />
          </div>
          <Tabs
            value={ui.tab}
            onValueChange={(v) => setUi((prev) => ({ ...prev, tab: v as AuthFormsMode }))}
            className="w-full"
          >
            <TabsList className={tabListClass}>
              <TabsTrigger value="login" className={tabTriggerClass}>
                로그인
              </TabsTrigger>
              <TabsTrigger value="signup" className={tabTriggerClass}>
                회원가입
              </TabsTrigger>
            </TabsList>

            <TabsContent value="login" className="mt-4">
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="login-username" className="text-neutral-700">
                    아이디
                  </Label>
                  <Input
                    id="login-username"
                    name="username"
                    type="text"
                    autoComplete="username"
                    placeholder="아이디"
                    className={inputClass}
                  />
                  {login.errors.username && (
                    <p className="text-xs text-red-600">{login.errors.username}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="login-password" className="text-neutral-700">
                    비밀번호
                  </Label>
                  <div className="relative">
                    <Input
                      id="login-password"
                      name="password"
                      type={ui.showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      placeholder="비밀번호"
                      className={cn(inputClass, "pr-10")}
                    />
                    {passwordToggle}
                  </div>
                  {login.errors.password && (
                    <p className="text-xs text-red-600">{login.errors.password}</p>
                  )}
                </div>
                {login.message && (
                  <p
                    className={`text-center text-sm ${
                      isSuccessMessage(login.message) ? "text-emerald-700" : "text-red-600"
                    }`}
                  >
                    {login.message}
                  </p>
                )}
                <Button
                  type="submit"
                  disabled={login.submitting}
                  className="w-full rounded-2xl bg-[#f0dc3a] font-bold text-neutral-900 shadow-sm hover:bg-[#e8d020]"
                >
                  {login.submitting ? "처리 중..." : "로그인"}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="signup" className="mt-4">
              <form onSubmit={handleSignup} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="signup-username" className="text-neutral-700">
                    아이디
                  </Label>
                  <Input
                    id="signup-username"
                    name="username"
                    type="text"
                    autoComplete="username"
                    placeholder="4자 이상"
                    className={inputClass}
                  />
                  {signup.errors.username && (
                    <p className="text-xs text-red-600">{signup.errors.username}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="signup-password" className="text-neutral-700">
                    비밀번호
                  </Label>
                  <div className="relative">
                    <Input
                      id="signup-password"
                      name="password"
                      type={ui.showPassword ? "text" : "password"}
                      autoComplete="new-password"
                      placeholder="6자 이상"
                      className={cn(inputClass, "pr-10")}
                    />
                    {passwordToggle}
                  </div>
                  {signup.errors.password && (
                    <p className="text-xs text-red-600">{signup.errors.password}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="signup-confirm" className="text-neutral-700">
                    비밀번호 확인
                  </Label>
                  <Input
                    id="signup-confirm"
                    name="confirmPassword"
                    type={ui.showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    placeholder="비밀번호 재입력"
                    className={inputClass}
                  />
                  {signup.errors.confirmPassword && (
                    <p className="text-xs text-red-600">{signup.errors.confirmPassword}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="signup-nickname" className="text-neutral-700">
                    닉네임
                  </Label>
                  <Input
                    id="signup-nickname"
                    name="nickname"
                    type="text"
                    autoComplete="nickname"
                    placeholder="닉네임"
                    className={inputClass}
                  />
                  {signup.errors.nickname && (
                    <p className="text-xs text-red-600">{signup.errors.nickname}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="signup-email" className="text-neutral-700">
                    이메일
                  </Label>
                  <Input
                    id="signup-email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    placeholder="example@email.com"
                    className={inputClass}
                  />
                  {signup.errors.email && (
                    <p className="text-xs text-red-600">{signup.errors.email}</p>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="signup-gender" className="text-neutral-700">
                      성별
                    </Label>
                    <select
                      id="signup-gender"
                      name="gender"
                      defaultValue="undisclosed"
                      className={`h-10 w-full rounded-md px-3 text-sm ${inputClass}`}
                    >
                      <option value="undisclosed">선택 안 함</option>
                      <option value="male">남성</option>
                      <option value="female">여성</option>
                      <option value="other">기타</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="signup-age-group" className="text-neutral-700">
                      연령대
                    </Label>
                    <select
                      id="signup-age-group"
                      name="age_group"
                      defaultValue="undisclosed"
                      className={`h-10 w-full rounded-md px-3 text-sm ${inputClass}`}
                    >
                      <option value="undisclosed">선택 안 함</option>
                      <option value="10s">10대</option>
                      <option value="20s">20대</option>
                      <option value="30s">30대</option>
                      <option value="40s">40대</option>
                      <option value="50s">50대</option>
                      <option value="60s_plus">60대 이상</option>
                    </select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="signup-birth-year" className="text-neutral-700">
                    출생 연도 (선택)
                  </Label>
                  <Input
                    id="signup-birth-year"
                    name="birth_year"
                    type="number"
                    min={1950}
                    max={2015}
                    placeholder="예: 1995"
                    className={inputClass}
                  />
                </div>
                {signup.message && (
                  <p
                    className={`text-center text-sm ${
                      isSuccessMessage(signup.message) ? "text-emerald-700" : "text-red-600"
                    }`}
                  >
                    {signup.message}
                  </p>
                )}
                <Button
                  type="submit"
                  disabled={signup.submitting}
                  className="w-full rounded-2xl bg-[#f0dc3a] font-bold text-neutral-900 shadow-sm hover:bg-[#e8d020]"
                >
                  {signup.submitting ? "처리 중..." : "가입하기"}
                </Button>
              </form>
            </TabsContent>
          </Tabs>

        {variant === "page" && (
          <p className="mt-6 text-center text-sm text-neutral-500">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-neutral-600 transition-colors hover:text-neutral-900"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              홈으로 돌아가기
            </Link>
          </p>
        )}
      </CardContent>
    </Card>
  )

  if (variant === "embedded") {
    return <div className="w-full bg-white">{card}</div>
  }

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center bg-[#e8e8e8] px-4 py-10 md:px-6">
      {card}
    </div>
  )
}
