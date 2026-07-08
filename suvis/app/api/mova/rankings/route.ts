import { type NextRequest, NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

export async function GET(request: NextRequest) {
  const source = request.nextUrl.searchParams.get("source") ?? "chat_trend"
  const limit = request.nextUrl.searchParams.get("limit") ?? "10"
  try {
    const res = await backendFetch(`/mova/rankings/hot?source=${encodeURIComponent(source)}&limit=${encodeURIComponent(limit)}`)
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
