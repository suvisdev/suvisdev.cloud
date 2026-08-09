import { NextRequest, NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ reviewId: string }> },
): Promise<NextResponse> {
  const { reviewId } = await params
  const auth = req.headers.get("authorization")
  try {
    const res = await backendFetch(`/mova/reviews/${encodeURIComponent(reviewId)}`, {
      method: "DELETE",
      headers: auth ? { Authorization: auth } : {},
    })
    const data: unknown = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: BACKEND_DOWN }, { status: 503 })
  }
}
