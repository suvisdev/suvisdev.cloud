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

/** 로그인 표시와 실제 인증을 맞춘다. 표시는 localStorage에 기한 없이 남지만 인증 쿠키는 만료되므로
 * (또는 쿠키 전환 전에 로그인해 쿠키가 아예 없을 수 있으므로) 둘이 어긋날 수 있다. whoami는 catch-all을
 * 거쳐 access가 만료됐으면 refresh로 갱신까지 하고, 그래도 401이면 표시를 지워 로그아웃 상태로 보여 준다.
 * 네트워크 오류·서버 장애(5xx)에서는 지우지 않는다 — 인증이 무효라고 확인된 경우만. */
export async function syncSessionWithCookie(): Promise<void> {
  if (!getSuvisSession()) return
  try {
    const res = await fetch("/api/backend/mova/whoami")
    if (res.status === 401) clearSuvisSession()
  } catch {
    // 확인하지 못했으면 표시를 그대로 둔다.
  }
}

const POST_LOGIN_KEY = "suvis_post_login_path"

/** 소셜 로그인은 외부로 나갔다 돌아오므로, 로그인 뒤 돌아갈 경로를 탭에 적어 둔다. */
export function rememberPostLoginPath(path: string): void {
  if (typeof window === "undefined") return
  try {
    window.sessionStorage.setItem(POST_LOGIN_KEY, path)
  } catch {
    // 저장 못 하면 기본 경로("/")로 돌아갈 뿐이다.
  }
}

/** 적어 둔 경로를 꺼내고 지운다. 사이트 안 경로("/…")만 받는다 — 외부 주소로 보내지 않는다. */
export function takePostLoginPath(): string {
  if (typeof window === "undefined") return "/"
  try {
    const path = window.sessionStorage.getItem(POST_LOGIN_KEY)
    window.sessionStorage.removeItem(POST_LOGIN_KEY)
    if (path && /^\/(?!\/)/.test(path)) return path
  } catch {
    // 아래 기본값으로
  }
  return "/"
}
