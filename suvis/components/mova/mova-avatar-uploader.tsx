"use client"

import { useEffect, useRef, useState } from "react"
import { Loader2, User } from "lucide-react"

import { fetchProfile, uploadAvatar } from "@/lib/profile-api"

export function MovaAvatarUploader({ userId }: { userId: number }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // mova 마이페이지 응답(MypageData)엔 아바타가 없어 프로필에서 따로 읽는다.
  // 실패해도 조용히 넘어간다 — 업로드 자체는 계속 쓸 수 있다.
  useEffect(() => {
    let alive = true
    fetchProfile(userId)
      .then((p) => alive && setAvatarUrl(p.avatar_url))
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [userId])

  // createObjectURL은 명시적으로 해제하지 않으면 페이지가 살아 있는 내내 남는다.
  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  }, [preview])

  async function handleSelect(file: File) {
    setError(null)
    setPreview((prev) => {
      if (prev) URL.revokeObjectURL(prev)
      return URL.createObjectURL(file)
    })
    setUploading(true)
    try {
      const { avatar_url } = await uploadAvatar(file)
      setAvatarUrl(avatar_url)
    } catch (e) {
      setError(e instanceof Error ? e.message : "프로필 사진을 올리지 못했습니다.")
      setPreview((prev) => {
        if (prev) URL.revokeObjectURL(prev)
        return null
      })
    } finally {
      setUploading(false)
    }
  }

  const shown = preview ?? avatarUrl

  return (
    <div className="flex flex-col items-center gap-1">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className="relative flex h-14 w-14 items-center justify-center overflow-hidden rounded-full bg-mova-accent-soft transition hover:opacity-80 disabled:opacity-50"
        aria-label="프로필 사진 변경"
      >
        {shown ? (
          // presigned URL은 1시간마다 바뀌어 next/image 최적화 캐시가 의미 없다.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={shown} alt="프로필 사진" className="h-full w-full object-cover" />
        ) : (
          <User className="h-7 w-7 text-mova-accent" />
        )}
        {uploading && (
          <span className="absolute inset-0 flex items-center justify-center bg-black/50">
            <Loader2 className="h-4 w-4 animate-spin text-white" />
          </span>
        )}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) void handleSelect(file)
          e.target.value = "" // 같은 파일을 다시 골라도 change가 나게 비운다
        }}
      />
      {error && <p className="max-w-[7rem] text-center text-[10px] text-rose-400">{error}</p>}
    </div>
  )
}
