import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

type RouteContext = { params: Promise<{ tmdbId: string }> }

export async function GET(_request: Request, context: RouteContext) {
  const { tmdbId } = await context.params

  try {
    const res = await backendFetch(`/mova/upcoming/${encodeURIComponent(tmdbId)}`, {
      next: { revalidate: 1800 },
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
