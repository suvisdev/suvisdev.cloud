"use client"

import Link from "next/link"
import { Suspense, useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { exchangeOAuthCode } from "@/lib/oauth-api"
import { saveSuvisSession } from "@/lib/suvis-session"

/** 백엔드 /viewer/oauth/{provider}/callback이 이리로 돌려보낸다.
 * type=session: 기존 연결 계정 — 바로 세션 교환 후 홈으로.
 * type=consent_required: 신규 신원 — 약관 동의 화면으로 넘긴다. */
function OAuthCallbackInner() {
  const router = useRouter()
  const params = useSearchParams()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const type = params.get("type")
    const code = params.get("code")
    if (!type || !code) {
      setError("잘못된 접근입니다.")
      return
    }

    if (type === "consent_required") {
      router.replace(`/oauth/consent?code=${encodeURIComponent(code)}`)
      return
    }

    if (type !== "session") {
      setError("알 수 없는 로그인 응답입니다.")
      return
    }

    exchangeOAuthCode(code)
      .then((session) => {
        saveSuvisSession(session)
        router.replace("/")
      })
      .catch((e: Error) => setError(e.message))
  }, [params, router])

  if (error) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center gap-3 bg-[#e8e8e8] px-4 text-center">
        <p className="text-sm font-medium text-red-600">{error}</p>
        <Link href="/" className="text-sm text-neutral-600 underline underline-offset-2">
          홈으로 돌아가기
        </Link>
      </div>
    )
  }

  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-[#e8e8e8]">
      <p className="text-sm text-neutral-500">로그인 처리 중...</p>
    </div>
  )
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-[#e8e8e8]">
          <p className="text-sm text-neutral-500">로그인 처리 중...</p>
        </div>
      }
    >
      <OAuthCallbackInner />
    </Suspense>
  )
}
