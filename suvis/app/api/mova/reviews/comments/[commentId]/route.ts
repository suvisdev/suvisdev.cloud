import { NextRequest, NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ commentId: string }> },
): Promise<NextResponse> {
  const { commentId } = await params
  const auth = req.headers.get("authorization")
  try {
    const res = await backendFetch(`/mova/reviews/comments/${encodeURIComponent(commentId)}`, {
      method: "DELETE",
      headers: auth ? { Authorization: auth } : {},
    })
    const data: unknown = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: BACKEND_DOWN }, { status: 502 })
  }
}
