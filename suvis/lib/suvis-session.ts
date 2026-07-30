/** Secom 회원 로그인 세션 — Suvisdev·Mova 공용 (localStorage). */

export type SuvisSession = {
  id: number
  username: string
  nickname?: string
  token?: string
  role?: "admin" | "user"
}

const STORAGE_KEY = "suvis_session"
export const SUVIS_SESSION_CHANGED_EVENT = "suvis-session-changed"

export function saveSuvisSession(session: SuvisSession): void {
  if (typeof window === "undefined") return
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  window.dispatchEvent(new Event(SUVIS_SESSION_CHANGED_EVENT))
}

export function getSuvisSession(): SuvisSession | null {
  if (typeof window === "undefined") return null
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as SuvisSession
    if (typeof data.id !== "number" || !data.username) return null
    return data
  } catch {
    return null
  }
}

/** 세션 토큰을 Authorization 헤더로 반환한다(없으면 빈 객체). */
export function authHeader(): Record<string, string> {
  const token = getSuvisSession()?.token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function clearSuvisSession(): void {
  if (typeof window === "undefined") return
  window.localStorage.removeItem(STORAGE_KEY)
  window.dispatchEvent(new Event(SUVIS_SESSION_CHANGED_EVENT))
}
