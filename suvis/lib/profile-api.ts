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
  avatar_url: string | null
}

type ProfileErrorBody = { detail?: string | unknown }

export async function fetchProfile(userId: number): Promise<ProfileResult> {
  const res = await fetch(`/api/viewer/profile?id=${userId}`, {
    cache: "no-store",
    headers: { ...authHeader() },
  })
  const data = (await res.json()) as ProfileResult & ProfileErrorBody
  if (!res.ok) {
    throw new Error(
      safeApiErrorMessage(data.detail, "프로필을 불러오지 못했습니다.", res.status),
    )
  }
  return data
}

async function patchProfile(
  userId: number,
  body: { nickname: string } | { preferred_genres: string[] },
  fallbackMessage: string,
): Promise<ProfileResult> {
  const res = await fetch(`/api/viewer/profile?id=${userId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(body),
  })
  const data = (await res.json()) as ProfileResult & ProfileErrorBody
  if (!res.ok) {
    throw new Error(safeApiErrorMessage(data.detail, fallbackMessage, res.status))
  }
  return data
}

export function updateNickname(userId: number, nickname: string): Promise<ProfileResult> {
  return patchProfile(userId, { nickname }, "닉네임을 변경하지 못했습니다.")
}

export async function uploadAvatar(file: File): Promise<{ avatar_url: string | null }> {
  const form = new FormData()
  form.append("file", file)
  // Content-Type은 브라우저가 boundary와 함께 붙인다 — 직접 넣으면 안 된다.
  const res = await fetch("/api/viewer/avatar", {
    method: "POST",
    headers: { ...authHeader() },
    body: form,
  })
  const data = (await res.json()) as { avatar_url: string | null } & ProfileErrorBody
  if (!res.ok) {
    throw new Error(
      safeApiErrorMessage(data.detail, "프로필 사진을 올리지 못했습니다.", res.status),
    )
  }
  return data
}

export function updatePreferredGenres(
  userId: number,
  preferredGenres: string[],
): Promise<ProfileResult> {
  return patchProfile(
    userId,
    { preferred_genres: preferredGenres },
    "선호 장르를 변경하지 못했습니다.",
  )
}
