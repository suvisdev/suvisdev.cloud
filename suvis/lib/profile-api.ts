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
