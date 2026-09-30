import { cookies } from "next/headers"
import { NextResponse } from "next/server"

import { REFRESH_COOKIE, clearAuthCookies, gatewayPost } from "@/lib/auth-bff"

// BFF 로그아웃 — 게이트웨이에서 refresh family를 revoke하고 쿠키를 지운다.
// 게이트웨이 호출이 실패해도 로컬 쿠키는 반드시 지운다(로그아웃은 최소한 클라에서 끊겨야 한다).
export async function POST() {
  const refresh = (await cookies()).get(REFRESH_COOKIE)?.value
  if (refresh) await gatewayPost("/auth/logout", { refresh_token: refresh }).catch(() => undefined)
  const response = NextResponse.json({ ok: true })
  clearAuthCookies(response)
  return response
}
