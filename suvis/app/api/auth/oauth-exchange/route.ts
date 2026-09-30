import { NextResponse } from "next/server"

import { setAccessCookie } from "@/lib/auth-bff"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

// OAuth 핸드오프 코드 교환 — 토큰을 httpOnly 쿠키로 심고 클라엔 사용자 정보만 준다(토큰 비노출).
export async function POST(request: Request) {
  try {
    const body = await request.json()
    const res = await backendFetch("/viewer/oauth/exchange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    let data: unknown
    try {
      data = await res.json()
    } catch {
      data = { detail: `Backend response error (${res.status})` }
    }
    if (!res.ok || typeof data !== "object" || data === null) {
      return NextResponse.json(data, { status: res.status })
    }
    const { token, ...user } = data as { token?: string } & Record<string, unknown>
    const response = NextResponse.json(user, { status: res.status })
    if (typeof token === "string") setAccessCookie(response, token)
    return response
  } catch {
    return NextResponse.json({ detail: BACKEND_DOWN }, { status: 502 })
  }
}
