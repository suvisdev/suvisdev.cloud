"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import { fetchProfile, type ProfileResult } from "@/lib/profile-api"
import { getSuvisSession } from "@/lib/suvis-session"

const GENDER_LABEL: Record<string, string> = {
  male: "남성",
  female: "여성",
  other: "기타",
  undisclosed: "선택 안 함",
}

const PROVIDER_LABEL: Record<string, string> = {
  google: "Google",
  kakao: "카카오",
  naver: "네이버",
}

export default function MyPage() {
  const router = useRouter()
  const [profile, setProfile] = useState<ProfileResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const session = getSuvisSession()
    if (!session) {
      router.replace("/")
      return
    }
    fetchProfile(session.id)
      .then(setProfile)
      .catch((e: Error) => setError(e.message))
  }, [router])

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

  if (!profile) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-[#e8e8e8]">
        <p className="text-sm text-neutral-500">불러오는 중...</p>
      </div>
    )
  }

  const rows: { label: string; value: string }[] = [
    { label: "아이디", value: profile.username },
    { label: "닉네임", value: profile.nickname },
    { label: "이메일", value: profile.email },
    { label: "성별", value: GENDER_LABEL[profile.gender] ?? profile.gender },
    {
      label: "연결된 로그인",
      value: profile.providers.length
        ? profile.providers.map((p) => PROVIDER_LABEL[p] ?? p).join(", ")
        : "아이디/비밀번호",
    },
  ]

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center bg-[#e8e8e8] px-4 py-10 md:px-6">
      <div className="w-full max-w-md rounded-3xl border border-neutral-300/80 bg-white p-6 shadow-lg shadow-neutral-900/5 sm:p-8">
        <h1 className="text-xl font-bold tracking-tight text-neutral-900">마이페이지</h1>
        <p className="mt-1 text-sm text-neutral-500">내 계정 정보</p>

        <div className="mt-6 divide-y divide-neutral-100">
          {rows.map((row) => (
            <div key={row.label} className="flex items-center justify-between py-3 text-sm">
              <span className="text-neutral-500">{row.label}</span>
              <span className="font-medium text-neutral-900">{row.value}</span>
            </div>
          ))}
        </div>

        <p className="mt-6 text-center text-sm">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-neutral-600 transition-colors hover:text-neutral-900"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            홈으로 돌아가기
          </Link>
        </p>
      </div>
    </div>
  )
}
