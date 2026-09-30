import { cookies } from "next/headers"
import { NextResponse } from "next/server"

import {
  REFRESH_COOKIE,
  clearAuthCookies,
  gatewayPost,
  parseTokenPair,
  setAuthCookies,
} from "@/lib/auth-bff"

// BFF 리프레시 — refresh 쿠키로 게이트웨이 /auth/refresh를 회전시켜 새 access를 쿠키에 심는다.
// 실패(만료·재사용탐지)면 쿠키를 지우고 401 — 호출부가 재로그인으로 보낸다.
export async function POST() {
  const refresh = (await cookies()).get(REFRESH_COOKIE)?.value
  if (!refresh) return NextResponse.json({ detail: "인증이 만료되었습니다." }, { status: 401 })
  const res = await gatewayPost("/auth/refresh", { refresh_token: refresh })
  const tokens = res.ok ? parseTokenPair(await res.json().catch(() => ({}))) : null
  if (!tokens) {
    const failed = NextResponse.json({ detail: "인증이 만료되었습니다." }, { status: 401 })
    clearAuthCookies(failed)
    return failed
  }
  const response = NextResponse.json({ ok: true })
  setAuthCookies(response, tokens)
  return response
}
