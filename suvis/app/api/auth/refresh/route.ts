import { NextResponse } from "next/server"

import { AUTH_UNAVAILABLE, refreshFromCookie } from "@/lib/auth-bff"

// BFF 리프레시 — refresh 쿠키로 게이트웨이 /auth/refresh를 회전시켜 새 access를 쿠키에 심는다.
// 토큰 무효(만료·재사용탐지)면 쿠키를 지우고 401 — 호출부가 재로그인으로 보낸다.
// 인증 서버 장애(5xx·네트워크)면 쿠키를 그대로 두고 503 — 세션을 끊지 않고 재시도하게 한다.
export async function POST() {
  const result = await refreshFromCookie()
  if (result?.kind === "unavailable") {
    return NextResponse.json({ detail: AUTH_UNAVAILABLE }, { status: 503 })
  }
  if (result?.kind !== "ok") {
    return NextResponse.json({ detail: "인증이 만료되었습니다." }, { status: 401 })
  }
  return NextResponse.json({ ok: true })
}
