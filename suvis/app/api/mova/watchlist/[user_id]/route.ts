import { NextRequest, NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ user_id: string }> },
): Promise<NextResponse> {
  const { user_id } = await params
  const auth = req.headers.get("authorization")
  try {
    const res = await backendFetch(`/mova/watchlist/${encodeURIComponent(user_id)}`, {
      cache: "no-store",
      headers: auth ? { Authorization: auth } : {},
    })
    const data: unknown = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: BACKEND_DOWN }, { status: 503 })
  }
}
