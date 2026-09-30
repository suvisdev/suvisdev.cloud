import { safeApiErrorMessage } from "@/lib/user-facing-error"

export type AdminUser = {
  id: number
  email: string
  nickname: string
  role: "admin" | "user"
  providers: string[]
  created_at: string
}

type ApiErrorBody = { detail?: string | unknown }

async function adminUsersFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/backend/viewer/admin/users${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
    },
  })
  const data = (await res.json()) as T & ApiErrorBody
  if (!res.ok) {
    throw new Error(safeApiErrorMessage(data.detail, "요청을 처리하지 못했습니다.", res.status))
  }
  return data
}

export function listAdminUsers(): Promise<AdminUser[]> {
  return adminUsersFetch<AdminUser[]>("")
}
