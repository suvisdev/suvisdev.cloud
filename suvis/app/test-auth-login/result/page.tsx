"use client"

import { Suspense, useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"

/** auth 게이트웨이가 /auth/callback/{provider} 완료 후 이리로 돌려보낸다
 * (?code=handoff_code). 이 code를 POST /auth/exchange로 실제 토큰과 맞바꾼 뒤,
 * 그 토큰이 실제로 mova API(/mova/whoami)에서 통하는지까지 확인하는 테스트 전용
 * 결과 페이지 — 기존 /oauth/callback(viewer용)과는 별개. */

const AUTH_BASE = "https://auth.suvisdev.cloud"
const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://127.0.0.1:8000"

type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

type WhoamiResponse = {
  sub: string
  roles: string[]
  aud: string
}

type Step = "exchanging" | "calling-whoami" | "done" | "error"

function TestAuthLoginResultInner() {
  const params = useSearchParams()
  const code = params.get("code")

  const [step, setStep] = useState<Step>("exchanging")
  const [error, setError] = useState<string | null>(null)
  const [tokens, setTokens] = useState<TokenResponse | null>(null)
  const [whoami, setWhoami] = useState<WhoamiResponse | null>(null)

  useEffect(() => {
    if (!code) {
      setStep("error")
      setError("URL에 code 파라미터가 없습니다.")
      return
    }

    let cancelled = false

    async function run() {
      try {
        const exchangeRes = await fetch(`${AUTH_BASE}/auth/exchange`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code }),
        })
        const exchangeBody = (await exchangeRes.json()) as TokenResponse & { detail?: string }
        if (!exchangeRes.ok) {
          throw new Error(
            `토큰 교환 실패 (${exchangeRes.status}): ${exchangeBody.detail ?? "알 수 없는 오류"}`,
          )
        }
        if (cancelled) return
        setTokens(exchangeBody)
        setStep("calling-whoami")

        const whoamiRes = await fetch(`${API_BASE}/mova/whoami`, {
          headers: { Authorization: `Bearer ${exchangeBody.access_token}` },
        })
        const whoamiBody = (await whoamiRes.json()) as WhoamiResponse & { detail?: string }
        if (!whoamiRes.ok) {
          throw new Error(
            `/mova/whoami 실패 (${whoamiRes.status}): ${whoamiBody.detail ?? "알 수 없는 오류"}`,
          )
        }
        if (cancelled) return
        setWhoami(whoamiBody)
        setStep("done")
      } catch (e) {
        if (cancelled) return
        setError(e instanceof Error ? e.message : "알 수 없는 오류가 발생했습니다.")
        setStep("error")
      }
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [code])

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-4 px-4 py-10">
      <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">
        auth 게이트웨이 로그인 테스트 결과
      </h1>

      <p className="text-sm text-neutral-600 dark:text-neutral-400">
        상태:{" "}
        {step === "exchanging" && "handoff code를 토큰과 교환 중..."}
        {step === "calling-whoami" && "발급된 토큰으로 /mova/whoami 호출 중..."}
        {step === "done" && "완료"}
        {step === "error" && "에러 발생"}
      </p>

      {error && (
        <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
          {error}
        </p>
      )}

      {tokens && (
        <div className="space-y-1 rounded-lg bg-neutral-100 p-3 text-xs dark:bg-neutral-800">
          <p className="font-semibold text-neutral-800 dark:text-neutral-200">
            /auth/exchange 응답
          </p>
          <p className="break-all text-neutral-600 dark:text-neutral-400">
            access_token: {tokens.access_token}
          </p>
          <p className="break-all text-neutral-600 dark:text-neutral-400">
            refresh_token: {tokens.refresh_token}
          </p>
          <p className="text-neutral-600 dark:text-neutral-400">
            expires_in: {tokens.expires_in}초
          </p>
        </div>
      )}

      {whoami && (
        <div className="space-y-1 rounded-lg bg-emerald-50 p-3 text-xs text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300">
          <p className="font-semibold">/mova/whoami 응답 — 토큰이 실제로 통했습니다</p>
          <p>sub: {whoami.sub}</p>
          <p>roles: {whoami.roles.join(", ")}</p>
          <p>aud: {whoami.aud}</p>
        </div>
      )}
    </div>
  )
}

export default function TestAuthLoginResultPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[60vh] items-center justify-center">
          <p className="text-sm text-neutral-500">로딩 중...</p>
        </div>
      }
    >
      <TestAuthLoginResultInner />
    </Suspense>
  )
}
