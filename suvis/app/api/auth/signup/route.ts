import { NextResponse } from "next/server"

import { AUTH_AUD, fetchUserInfo, gatewayPost, parseTokenPair, setAuthCookies } from "@/lib/auth-bff"
import { BACKEND_DOWN } from "@/lib/backend-client"

// BFF 회원가입 — 게이트웨이가 가입 즉시 토큰을 주므로 로그인과 동일하게 쿠키를 심는다(auto-login).
export async function POST(request: Request) {
  try {
    const body = (await request.json()) as Record<string, unknown>
    const res = await gatewayPost("/auth/signup", { ...body, aud: AUTH_AUD })
    const data: unknown = await res.json().catch(() => ({}))
    const tokens = res.ok ? parseTokenPair(data) : null
    if (!tokens) return NextResponse.json(data, { status: res.ok ? 502 : res.status })
    const user = await fetchUserInfo(tokens.access_token)
    const response = NextResponse.json(user, { status: 201 })
    setAuthCookies(response, tokens)
    return response
  } catch {
    return NextResponse.json({ detail: BACKEND_DOWN }, { status: 502 })
  }
}
