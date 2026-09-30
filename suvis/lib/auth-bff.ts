// 서버(라우트 핸들러) 전용 BFF 인증 헬퍼.
// access·refresh 토큰을 httpOnly 쿠키에 담고, auth 게이트웨이(별도 도메인) 호출을 서버측에서 대행한다.
// 목적: 토큰을 클라이언트 JS에 절대 노출하지 않는다(구 localStorage 방식은 XSS로 탈취 가능했다).
// 백엔드는 이미 access+refresh를 발급하고 /auth/refresh·/auth/logout이 있다 — 여기선 쿠키 배선만 한다.
import type { NextResponse } from "next/server"

const AUTH_BASE = process.env.AUTH_URL || "https://auth.suvisdev.cloud"
const API_BASE =
  process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
export const AUTH_AUD = "suvis-mova"

export const ACCESS_COOKIE = "sv_access"
export const REFRESH_COOKIE = "sv_refresh"
const REFRESH_MAX_AGE = 60 * 60 * 24 * 14 // 14일 — 백엔드 RefreshTokenStore TTL과 일치

export type TokenPair = { access_token: string; refresh_token: string; expires_in: number }
export type UserInfo = { id: number; username: string }

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  }
}

export function setAuthCookies(res: NextResponse, tokens: TokenPair): void {
  res.cookies.set(ACCESS_COOKIE, tokens.access_token, cookieOptions(tokens.expires_in))
  res.cookies.set(REFRESH_COOKIE, tokens.refresh_token, cookieOptions(REFRESH_MAX_AGE))
}

export function clearAuthCookies(res: NextResponse): void {
  // maxAge 0 = 즉시 만료. path를 맞춰 지워야 브라우저가 실제로 제거한다.
  res.cookies.set(ACCESS_COOKIE, "", cookieOptions(0))
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
  const who = (await res.json()) as { sub: string; username?: string }
  return { id: Number(who.sub), username: who.username || `user-${who.sub}` }
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
