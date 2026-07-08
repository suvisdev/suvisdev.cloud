import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

type RouteContext = { params: Promise<{ movieId: string }> }

export async function GET(_request: Request, context: RouteContext) {
  const { movieId } = await context.params

  try {
    const res = await backendFetch(
      `/mova/reviews/rating/${encodeURIComponent(movieId)}`,
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
