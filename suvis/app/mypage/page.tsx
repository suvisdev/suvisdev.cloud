"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, Check, Pencil, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { fetchProfile, updateNickname, type ProfileResult } from "@/lib/profile-api"
import { getSuvisSession, saveSuvisSession } from "@/lib/suvis-session"

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
  const [editingNickname, setEditingNickname] = useState(false)
  const [nicknameInput, setNicknameInput] = useState("")
  const [nicknameError, setNicknameError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

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

  const startEditingNickname = () => {
    if (!profile) return
    setNicknameInput(profile.nickname)
    setNicknameError(null)
    setEditingNickname(true)
  }

  const cancelEditingNickname = () => {
    setEditingNickname(false)
    setNicknameError(null)
  }

  const saveNickname = async () => {
    const session = getSuvisSession()
    const trimmed = nicknameInput.trim()
    if (!session || !trimmed) return
    setSaving(true)
    setNicknameError(null)
    try {
      const updated = await updateNickname(session.id, trimmed)
      setProfile(updated)
      saveSuvisSession({ ...session, nickname: updated.nickname })
      setEditingNickname(false)
    } catch (e) {
      setNicknameError(e instanceof Error ? e.message : "닉네임을 변경하지 못했습니다.")
    } finally {
      setSaving(false)
    }
  }

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
          <div className="py-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-neutral-500">닉네임</span>
              {editingNickname ? (
                <div className="flex items-center gap-1.5">
                  <Input
                    value={nicknameInput}
                    onChange={(e) => setNicknameInput(e.target.value)}
                    maxLength={50}
                    autoFocus
                    className="h-7 w-32 text-sm"
                    disabled={saving}
                  />
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    onClick={saveNickname}
                    disabled={saving || !nicknameInput.trim()}
                    aria-label="닉네임 저장"
                  >
                    <Check className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    onClick={cancelEditingNickname}
                    disabled={saving}
                    aria-label="닉네임 편집 취소"
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={startEditingNickname}
                  className="inline-flex items-center gap-1.5 font-medium text-neutral-900 transition-colors hover:text-neutral-600"
                >
                  {profile.nickname}
                  <Pencil className="h-3 w-3 text-neutral-400" aria-hidden />
                </button>
              )}
            </div>
            {nicknameError && (
              <p className="mt-1 text-right text-xs text-red-600">{nicknameError}</p>
            )}
          </div>
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
