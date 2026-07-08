/** Secom 회원 로그인 세션 — Suvisdev·Mova 공용 (localStorage). */

export type SuvisSession = {
  id: number
  username: string
}

const STORAGE_KEY = "suvis_session"

export function saveSuvisSession(session: SuvisSession): void {
  if (typeof window === "undefined") return
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
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

export function clearSuvisSession(): void {
  if (typeof window === "undefined") return
  window.localStorage.removeItem(STORAGE_KEY)
}
