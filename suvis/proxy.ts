import { NextResponse, type NextRequest } from "next/server"

import {
  ACCESS_COOKIE,
  AUTH_UNAVAILABLE,
  REFRESH_COOKIE,
  clearTokens,
  isExpired,
  refreshOnce,
  writeTokens,
} from "@/lib/auth-bff"

// /api/** 라우트 앞에서 access 쿠키를 한 번에 갱신한다 — 개별 프록시 30여 곳이 각자 갱신하지 않게.
// access가 없거나 만료 직전이고 refresh가 있으면 회전한다.
// - 성공: 새 토큰을 이 요청의 쿠키로 바꿔 라우트에 넘기고, 응답 쿠키에도 심는다.
// - 무효(401/403): 쿠키를 지우고 비로그인으로 넘긴다(세션이 실제로 끝났다).
// - 인증 서버 장애: 라우트로 보내지 않고 503 — 만료 토큰으로 401이 나거나 /mova/chat이 익명으로
//   강등되지 않게 한다. 쿠키는 그대로 두니 클라가 재시도하면 된다.
export async function proxy(request: NextRequest) {
  const access = request.cookies.get(ACCESS_COOKIE)?.value
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value
  if (!refresh || (access && !isExpired(access))) return NextResponse.next()

  const result = await refreshOnce(refresh)
  if (result.kind === "unavailable") {
    return NextResponse.json({ detail: AUTH_UNAVAILABLE }, { status: 503 })
  }
  if (result.kind === "ok") {
    request.cookies.set(ACCESS_COOKIE, result.tokens.access_token)
    request.cookies.set(REFRESH_COOKIE, result.tokens.refresh_token)
  } else {
    request.cookies.delete(ACCESS_COOKIE)
    request.cookies.delete(REFRESH_COOKIE)
  }
  const headers = new Headers(request.headers)
  headers.set("cookie", request.cookies.toString())
  const response = NextResponse.next({ request: { headers } })
  if (result.kind === "ok") writeTokens(response.cookies, result.tokens)
  else clearTokens(response.cookies)
  return response
}

// /api/auth/**(로그인·로그아웃·refresh 자체)는 제외한다.
export const config = { matcher: ["/api/((?!auth/).*)"] }
