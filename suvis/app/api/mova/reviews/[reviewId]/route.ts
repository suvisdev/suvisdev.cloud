import type { NextRequest} from "next/server";
import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"
import { cookieBearer } from "@/lib/auth-bff"

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ reviewId: string }> },
): Promise<NextResponse> {
  const { reviewId } = await params
  const auth = await cookieBearer()
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
