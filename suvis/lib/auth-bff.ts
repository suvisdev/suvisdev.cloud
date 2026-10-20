// 서버(라우트 핸들러) 전용 BFF 인증 헬퍼.
// access·refresh 토큰을 httpOnly 쿠키에 담고, auth 게이트웨이(별도 도메인) 호출을 서버측에서 대행한다.
// 목적: 토큰을 클라이언트 JS에 절대 노출하지 않는다(구 localStorage 방식은 XSS로 탈취 가능했다).
// 백엔드는 이미 access+refresh를 발급하고 /auth/refresh·/auth/logout이 있다 — 여기선 쿠키 배선만 한다.
import { cookies } from "next/headers"
import { NextResponse } from "next/server"

const AUTH_BASE = process.env.AUTH_URL || "https://auth.suvisdev.cloud"
const API_BASE =
  process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
export const AUTH_AUD = "suvis-mova"

export const ACCESS_COOKIE = "sv_access"
export const REFRESH_COOKIE = "sv_refresh"
const REFRESH_MAX_AGE = 60 * 60 * 24 * 14 // 14일 — 백엔드 RefreshTokenStore TTL과 일치

export type TokenPair = { access_token: string; refresh_token: string; expires_in: number }
// role은 표시용(어드민 메뉴·AdminAuthGate) — 실제 접근 통제는 백엔드 require_admin이 JWT로 한다.
export type UserInfo = { id: number; username: string; role: "admin" | "user" }
type CookieJar = Pick<NextResponse["cookies"], "set">

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  }
}

function writeTokens(jar: CookieJar, tokens: TokenPair): void {
  jar.set(ACCESS_COOKIE, tokens.access_token, cookieOptions(tokens.expires_in))
  jar.set(REFRESH_COOKIE, tokens.refresh_token, cookieOptions(REFRESH_MAX_AGE))
}

function clearTokens(jar: CookieJar): void {
  // maxAge 0 = 즉시 만료. path를 맞춰 지워야 브라우저가 실제로 제거한다.
  jar.set(ACCESS_COOKIE, "", cookieOptions(0))
  jar.set(REFRESH_COOKIE, "", cookieOptions(0))
}

export function setAuthCookies(res: NextResponse, tokens: TokenPair): void {
  writeTokens(res.cookies, tokens)
}

export function clearAuthCookies(res: NextResponse): void {
  clearTokens(res.cookies)
}

const ACCESS_MAX_AGE = 60 * 60 * 24 * 7 // 7일 — access 토큰 TTL과 일치

// OAuth 교환은 access 토큰만 준다(refresh 없음). 이전 로그인(비밀번호)의 refresh 쿠키가 남아 있으면
// 새 access가 만료될 때 그 refresh로 갱신돼 **이전 계정으로** 요청이 나간다 — 게이트웨이에서 폐기하고 쿠키도 지운다.
export async function setAccessCookie(res: NextResponse, token: string): Promise<void> {
  const oldRefresh = (await cookies()).get(REFRESH_COOKIE)?.value
  if (oldRefresh) {
    // 폐기 실패(게이트웨이 장애)여도 쿠키는 지운다 — 남은 refresh는 TTL로 만료된다.
    await gatewayPost("/auth/logout", { refresh_token: oldRefresh }).catch(() => undefined)
  }
  res.cookies.set(ACCESS_COOKIE, token, cookieOptions(ACCESS_MAX_AGE))
  res.cookies.set(REFRESH_COOKIE, "", cookieOptions(0))
}

// auth 게이트웨이 POST 대행(로그인·회원가입·리프레시·로그아웃 공용).
export function gatewayPost(path: string, body: unknown): Promise<Response> {
  return fetch(`${AUTH_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}

// access 토큰으로 사용자 식별자를 조회한다(로그인 응답에 담아 클라 UI 게이팅에 쓴다 — 토큰은 안 준다).
export async function fetchUserInfo(accessToken: string): Promise<UserInfo> {
  const res = await fetch(`${API_BASE}/mova/whoami`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) throw new Error("사용자 정보를 불러오지 못했습니다.")
  const who = (await res.json()) as { sub: string; username?: string; roles?: string[] }
  return {
    id: Number(who.sub),
    username: who.username || `user-${who.sub}`,
    role: who.roles?.includes("admin") ? "admin" : "user",
  }
}

// 토큰쌍 응답을 파싱해 유효하면 반환, 아니면 null(에러 본문은 raw로 넘겨 호출부가 처리).
export function parseTokenPair(data: unknown): TokenPair | null {
  if (typeof data !== "object" || data === null) return null
  const d = data as Record<string, unknown>
  if (typeof d.access_token === "string" && typeof d.refresh_token === "string") {
    return {
      access_token: d.access_token,
      refresh_token: d.refresh_token,
      expires_in: typeof d.expires_in === "number" ? d.expires_in : 3600,
    }
  }
  return null
}

export type RefreshResult =
  | { kind: "ok"; tokens: TokenPair }
  | { kind: "invalid" } // 게이트웨이가 401/403 — 만료·재사용 탐지. 쿠키를 지운다.
  | { kind: "unavailable" } // 5xx·네트워크 오류 — 세션은 살아 있을 수 있으니 쿠키를 두고 재시도하게 한다.

export const AUTH_UNAVAILABLE = "인증 서버에 잠시 연결할 수 없습니다. 잠시 후 다시 시도해 주세요."

async function rotateRefresh(refresh: string): Promise<RefreshResult> {
  try {
    const r = await gatewayPost("/auth/refresh", { refresh_token: refresh })
    if (r.status === 401 || r.status === 403) return { kind: "invalid" }
    const tokens = r.ok ? parseTokenPair(await r.json().catch(() => ({}))) : null
    return tokens ? { kind: "ok", tokens } : { kind: "unavailable" }
  } catch {
    return { kind: "unavailable" }
  }
}

// 같은 refresh로 동시에 들어온 갱신을 하나로 합친다. 백엔드는 이미 쓴 refresh가 다시 오면 family 전체를
// 폐기하므로(refresh_store.rotate), 여러 요청이 각자 회전하면 정상 세션이 끊긴다. 끝난 뒤에도 잠깐
// 결과를 남겨, 새 쿠키가 브라우저에 반영되기 전에 옛 refresh로 출발한 요청도 같은 결과를 받게 한다.
// 남은 위험: 이 맵은 서버 인스턴스(프로세스) 안에서만 공유된다 — Vercel이 동시 요청을 서로 다른
// 인스턴스로 보내면 여전히 재사용 탐지에 걸릴 수 있다. 완전히 막으려면 백엔드가 직전 refresh를 짧게 유예해야 한다.
const REUSE_GRACE_MS = 10_000
const refreshing = new Map<string, Promise<RefreshResult>>()

function refreshOnce(refresh: string): Promise<RefreshResult> {
  const pending = refreshing.get(refresh)
  if (pending) return pending
  const p = rotateRefresh(refresh)
  refreshing.set(refresh, p)
  void p.then((r) => {
    // 일시 장애 결과는 남기지 않는다 — 다음 요청이 바로 다시 시도할 수 있게.
    setTimeout(() => refreshing.delete(refresh), r.kind === "unavailable" ? 0 : REUSE_GRACE_MS)
  })
  return p
}

// refresh 쿠키로 회전하고 결과를 이 요청의 응답 쿠키에 반영한다(성공=새 쿠키, 무효=삭제, 장애=그대로).
// refresh 쿠키가 없으면 null. cookies().set은 라우트 핸들러에서만 되므로 라우트 핸들러에서만 부른다.
export async function refreshFromCookie(): Promise<RefreshResult | null> {
  const store = await cookies()
  const refresh = store.get(REFRESH_COOKIE)?.value
  if (!refresh) return null
  const result = await refreshOnce(refresh)
  if (result.kind === "ok") writeTokens(store, result.tokens)
  else if (result.kind === "invalid") clearTokens(store)
  return result
}

// JWT exp만 본다(서명 검증은 백엔드 몫). 못 읽으면 만료 아님으로 두고 백엔드 판정(401)에 맡긴다.
function isExpired(jwt: string): boolean {
  try {
    const payload = JSON.parse(
      Buffer.from(jwt.split(".")[1] ?? "", "base64url").toString(),
    ) as { exp?: unknown }
    return typeof payload.exp === "number" && payload.exp * 1000 < Date.now() + 30_000
  } catch {
    return false
  }
}

// 프록시 pass-through 교체용 — 구 `request.headers.get("authorization")`(문자열 or null)과 같은 모양을
// 쿠키에서 만든다. 기존 `auth ? { Authorization: auth } : {}` 코드를 그대로 두고 이 값만 바꿔 끼운다.
// access가 없거나(쿠키 maxAge=토큰 TTL이라 만료되면 브라우저가 지운다) 만료 직전이면 refresh로 먼저
// 회전한다 — 개별 프록시도 갱신되고, 로그인 선택인 /mova/chat이 조용히 익명으로 떨어지지 않는다.
export async function cookieBearer(): Promise<string | undefined> {
  let access = (await cookies()).get(ACCESS_COOKIE)?.value
  if (!access || isExpired(access)) {
    const r = await refreshFromCookie()
    if (r?.kind === "ok") access = r.tokens.access_token
    else if (r?.kind === "invalid") access = undefined
  }
  return access ? `Bearer ${access}` : undefined
}

const BODYLESS = new Set(["GET", "HEAD"])
// user-agent는 방문자 집계의 봇 판정(analytics ping)이 본다 — 빼면 백엔드엔 Node의 UA만 보인다.
const FORWARD_HEADERS = ["content-type", "accept", "user-agent"]

// 백엔드로 요청을 대행하는 공용 프록시 — catch-all과 개별 프록시 라우트가 모두 이걸 쓴다.
// httpOnly access 쿠키를 Bearer로 붙이고, 401이면 refresh 쿠키로 한 번 회전 후 재시도한다(리프레시를 한 곳에).
// 클라이언트는 토큰을 갖지 않는다 — 인증은 쿠키가 진다.
export async function forwardToBackend(
  request: Request,
  backendUrl: string,
  method: string,
): Promise<NextResponse> {
  const body = BODYLESS.has(method) ? undefined : await request.arrayBuffer()
  const baseHeaders: Record<string, string> = {}
  for (const h of FORWARD_HEADERS) {
    const v = request.headers.get(h)
    if (v) baseHeaders[h] = v
  }

  const call = (bearer: string | undefined): Promise<Response> =>
    fetch(backendUrl, {
      method,
      headers: bearer ? { ...baseHeaders, authorization: bearer } : baseHeaders,
      body,
      redirect: "manual",
    })

  // 쿠키 갱신·삭제는 refreshFromCookie가 cookies()에 기록한다 — 아래에서 만드는 응답에 함께 실린다.
  let backendRes = await call(await cookieBearer())
  if (backendRes.status === 401) {
    const r = await refreshFromCookie()
    if (r?.kind === "ok") backendRes = await call(`Bearer ${r.tokens.access_token}`)
    // 인증 서버 장애를 401로 돌려주면 클라가 로그아웃 처리한다 — 재시도 가능한 503으로 구분한다.
    else if (r?.kind === "unavailable") {
      return NextResponse.json({ detail: AUTH_UNAVAILABLE }, { status: 503 })
    }
  }

  // 본문이 없어야 하는 상태(삭제 성공 204 등)에 빈 버퍼라도 실으면 Response 생성이 던진다.
  const bodyless = [204, 205, 304].includes(backendRes.status)
  const buf = bodyless ? null : await backendRes.arrayBuffer()
  return new NextResponse(buf, {
    status: backendRes.status,
    headers: { "content-type": backendRes.headers.get("content-type") ?? "application/json" },
  })
}
