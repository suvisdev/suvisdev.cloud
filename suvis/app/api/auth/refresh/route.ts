import { NextResponse } from "next/server"

import { refreshFromCookie, retryLaterResponse } from "@/lib/auth-bff"

// BFF 리프레시 — refresh 쿠키로 게이트웨이 /auth/refresh를 회전시켜 새 access를 쿠키에 심는다.
// 토큰 무효(만료·재사용탐지)면 쿠키를 지우고 401 — 호출부가 재로그인으로 보낸다.
// 인증 서버 장애(5xx·네트워크)면 503, 회전 경합(409 refresh_superseded)이면 409 — 둘 다 쿠키를 그대로 둔다.
export async function POST() {
  const result = await refreshFromCookie()
  const retry = retryLaterResponse(result)
  if (retry) return retry
  if (result?.kind !== "ok") {
    return NextResponse.json({ detail: "인증이 만료되었습니다." }, { status: 401 })
  }
  return NextResponse.json({ ok: true })
}
