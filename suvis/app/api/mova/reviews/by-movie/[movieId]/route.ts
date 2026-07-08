import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

type RouteContext = { params: Promise<{ movieId: string }> }

export async function GET(request: Request, context: RouteContext) {
  const { movieId } = await context.params
  const { searchParams } = new URL(request.url)
  const limit = searchParams.get("limit") ?? "20"
  const offset = searchParams.get("offset") ?? "0"

  try {
    const res = await backendFetch(
      `/mova/reviews/by-movie/${encodeURIComponent(movieId)}?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`,
      { cache: "no-store" },
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
