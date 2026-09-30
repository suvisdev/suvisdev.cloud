import { type NextRequest, NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"
import { cookieBearer } from "@/lib/auth-bff"

export async function POST(request: NextRequest) {
  const source = request.nextUrl.searchParams.get("source") ?? "chat_trend"
  const auth = await cookieBearer()
  try {
    const res = await backendFetch(
      `/mova/rankings/refresh?source=${encodeURIComponent(source)}`,
      { method: "POST", headers: auth ? { Authorization: auth } : {} },
    )
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
