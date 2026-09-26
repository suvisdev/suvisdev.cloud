import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

// 홈 포트폴리오 AI 채팅 프록시 — 무인증 공개 엔드포인트라 Authorization은 넘기지 않는다.
export async function POST(request: Request) {
  try {
    const body = await request.json()
    const res = await backendFetch("/portfolio/chat", {
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
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: BACKEND_DOWN }, { status: 502 })
  }
}
