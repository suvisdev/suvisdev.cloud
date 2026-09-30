import { NextResponse } from "next/server"

import { AUTH_AUD, fetchUserInfo, gatewayPost, parseTokenPair, setAuthCookies } from "@/lib/auth-bff"
import { BACKEND_DOWN } from "@/lib/backend-client"

// BFF 로그인 — 게이트웨이에서 access+refresh를 받아 httpOnly 쿠키로 심고, 클라엔 사용자 정보만 준다(토큰 비노출).
export async function POST(request: Request) {
  try {
    const body = (await request.json()) as Record<string, unknown>
    const res = await gatewayPost("/auth/login", { ...body, aud: AUTH_AUD })
    const data: unknown = await res.json().catch(() => ({}))
    const tokens = res.ok ? parseTokenPair(data) : null
    if (!tokens) return NextResponse.json(data, { status: res.ok ? 502 : res.status })
    const user = await fetchUserInfo(tokens.access_token)
    const response = NextResponse.json(user)
    setAuthCookies(response, tokens)
    return response
  } catch {
    return NextResponse.json({ detail: BACKEND_DOWN }, { status: 502 })
  }
}
