import { authHeader } from "@/lib/suvis-session"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

export type ProfileResult = {
  id: number
  username: string
  nickname: string
  email: string
  gender: string
  preferred_genres: string[]
  providers: string[]
}

type ProfileErrorBody = { detail?: string | unknown }

export async function fetchProfile(userId: number): Promise<ProfileResult> {
  const res = await fetch(`/api/viewer/profile?id=${userId}`, { cache: "no-store" })
  const data = (await res.json()) as ProfileResult & ProfileErrorBody
  if (!res.ok) {
    throw new Error(
      safeApiErrorMessage(data.detail, "프로필을 불러오지 못했습니다.", res.status),
    )
  }
  return data
}

export async function updateNickname(userId: number, nickname: string): Promise<ProfileResult> {
  const res = await fetch(`/api/viewer/profile?id=${userId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify({ nickname }),
  })
  const data = (await res.json()) as ProfileResult & ProfileErrorBody
  if (!res.ok) {
    throw new Error(
      safeApiErrorMessage(data.detail, "닉네임을 변경하지 못했습니다.", res.status),
    )
  }
  return data
}
