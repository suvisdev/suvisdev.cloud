import { getSuvisSession } from "@/lib/suvis-session"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://127.0.0.1:8000"

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
  const token = getSuvisSession()?.token
  const res = await fetch(`${API_BASE}/viewer/admin/users${path}`, {
    ...init,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
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
