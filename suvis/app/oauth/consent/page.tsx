"use client"

import { Suspense, useMemo, useState } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { Check } from "lucide-react"
import { submitOAuthConsent } from "@/lib/oauth-api"
import { saveSuvisSession } from "@/lib/suvis-session"
import { cn } from "@/lib/utils"

type ConsentItem = {
  id: string
  required: boolean
  label: string
  href?: string
}

const CONSENT_ITEMS: ConsentItem[] = [
  { id: "terms", required: true, label: "Suvisdev 이용약관", href: "/terms" },
  { id: "privacy", required: true, label: "개인정보 수집 및 이용 동의", href: "/privacy" },
  { id: "marketing", required: false, label: "마케팅 정보 수신 동의 (이메일)" },
]

function ConsentRow({
  item,
  checked,
  onToggle,
}: {
  item: ConsentItem
  checked: boolean
  onToggle: () => void
}) {
  return (
    <div className="flex items-center justify-between py-2.5">
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center gap-2.5 text-left text-sm text-neutral-800"
      >
        <span
          className={cn(
            "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors",
            checked
              ? "border-[#f0dc3a] bg-[#f0dc3a] text-neutral-900"
              : "border-neutral-300 text-transparent",
          )}
        >
          <Check className="h-3.5 w-3.5" strokeWidth={3} />
        </span>
        <span>
          <span className={item.required ? "text-neutral-900" : "text-neutral-600"}>
            ({item.required ? "필수" : "선택"}) {item.label}
          </span>
        </span>
      </button>
      {item.href && (
        <Link
          href={item.href}
          target="_blank"
          className="text-xs text-neutral-400 underline-offset-2 hover:text-neutral-600 hover:underline"
        >
          보기
        </Link>
      )}
    </div>
  )
}

function OAuthConsentInner() {
  const router = useRouter()
  const params = useSearchParams()
  const code = params.get("code") ?? ""

  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set())
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const allChecked = checkedIds.size === CONSENT_ITEMS.length
  const requiredSatisfied = useMemo(
    () => CONSENT_ITEMS.filter((i) => i.required).every((i) => checkedIds.has(i.id)),
    [checkedIds],
  )

  const toggle = (id: string) => {
    setCheckedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    setCheckedIds(allChecked ? new Set() : new Set(CONSENT_ITEMS.map((i) => i.id)))
  }

  const handleAgree = async () => {
    if (!code || !requiredSatisfied) return
    setSubmitting(true)
    setError(null)
    try {
      const session = await submitOAuthConsent(code, true)
      saveSuvisSession(session)
      router.replace("/")
    } catch (e) {
      setError(e instanceof Error ? e.message : "동의 처리에 실패했습니다.")
      setSubmitting(false)
    }
  }

  const handleCancel = async () => {
    if (code) {
      submitOAuthConsent(code, false).catch(() => {})
    }
    router.replace("/")
  }

  if (!code) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center gap-3 bg-[#e8e8e8] px-4 text-center">
        <p className="text-sm font-medium text-red-600">잘못된 접근입니다.</p>
        <Link href="/" className="text-sm text-neutral-600 underline underline-offset-2">
          홈으로 돌아가기
        </Link>
      </div>
    )
  }

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center bg-[#e8e8e8] px-4 py-10 md:px-6">
      <div className="w-full max-w-md rounded-3xl border border-neutral-300/80 bg-white p-6 shadow-lg shadow-neutral-900/5 sm:p-8">
        <h1 className="text-center text-xl font-bold tracking-tight text-neutral-900">
          Suvis<span className="font-extrabold">dev</span> 서비스 약관 동의
        </h1>
        <p className="mt-1.5 text-center text-sm text-neutral-500">
          처음 로그인하신 계정이에요. 계속하려면 아래 약관에 동의해 주세요.
        </p>

        <div className="mt-6 border-b border-neutral-200 pb-2.5">
          <button
            type="button"
            onClick={toggleAll}
            className="flex items-center gap-2.5 text-sm font-semibold text-neutral-900"
          >
            <span
              className={cn(
                "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors",
                allChecked
                  ? "border-[#f0dc3a] bg-[#f0dc3a] text-neutral-900"
                  : "border-neutral-300 text-transparent",
              )}
            >
              <Check className="h-3.5 w-3.5" strokeWidth={3} />
            </span>
            전체 동의하기
          </button>
        </div>

        <div className="divide-y divide-neutral-100">
          {CONSENT_ITEMS.map((item) => (
            <ConsentRow
              key={item.id}
              item={item}
              checked={checkedIds.has(item.id)}
              onToggle={() => toggle(item.id)}
            />
          ))}
        </div>

        <div className="mt-5 rounded-xl bg-neutral-50 p-3.5">
          <p className="text-xs font-semibold text-neutral-500">안내사항</p>
          <p className="mt-1 text-xs leading-relaxed text-neutral-500">
            본 서비스는 소셜 계정을 통한 로그인 기능을 이용하고 있습니다. 서비스 제공에 대한
            의무와 책임은 Suvisdev에 있으며, 동의 시 수집된 정보는 Suvisdev의 이용약관 및
            개인정보처리방침에 따라 관리됩니다.
          </p>
        </div>

        {error && <p className="mt-4 text-center text-sm text-red-600">{error}</p>}

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={handleCancel}
            className="flex-1 rounded-2xl border border-neutral-300 py-2.5 text-sm font-semibold text-neutral-600 transition-colors hover:bg-neutral-50"
          >
            취소
          </button>
          <button
            type="button"
            onClick={handleAgree}
            disabled={!requiredSatisfied || submitting}
            className="flex-1 rounded-2xl bg-[#f0dc3a] py-2.5 text-sm font-bold text-neutral-900 shadow-sm transition-colors hover:bg-[#e8d020] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "처리 중..." : "동의하고 가입하기"}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function OAuthConsentPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-[#e8e8e8]">
          <p className="text-sm text-neutral-500">불러오는 중...</p>
        </div>
      }
    >
      <OAuthConsentInner />
    </Suspense>
  )
}
