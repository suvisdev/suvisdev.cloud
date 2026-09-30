/** Secom 회원 로그인 세션 — UI 게이팅용 표시 정보(id·username·role).
 *
 * 토큰은 httpOnly 쿠키(sv_access·sv_refresh)에 있고 localStorage에 두지 않는다
 * (2026-09-30 BFF 쿠키 전환 — 구 localStorage 토큰은 XSS로 탈취 가능했다). 인증은 쿠키가 지고,
 * 인증 호출은 프록시(`/api/backend` 및 개별 `/api/*`)가 쿠키를 읽어 Bearer로 붙인다. 여기 저장하는 건
 * 화면 표시용 식별자뿐이다(민감정보 아님). role도 표시용 — 실제 접근 통제는 백엔드 require_admin이 한다
 * (.claude/rules/security/auth.md §2). */

export type SuvisSession = {
  id: number
  username: string
  nickname?: string
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

export function clearSuvisSession(): void {
  if (typeof window === "undefined") return
  window.localStorage.removeItem(STORAGE_KEY)
  window.dispatchEvent(new Event(SUVIS_SESSION_CHANGED_EVENT))
}

/** 로그아웃 — BFF가 refresh를 revoke하고 httpOnly 쿠키를 지운 뒤 로컬 UI 세션을 정리한다.
 * (localStorage만 지우면 쿠키가 남아 서버 세션이 유효한 채로 남는다.) */
export async function logoutSession(): Promise<void> {
  try {
    await fetch("/api/auth/logout", { method: "POST" })
  } catch {
    // 쿠키 삭제 실패해도 로컬 UI 세션은 반드시 정리한다.
  }
  clearSuvisSession()
}
