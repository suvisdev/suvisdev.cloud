import type { NextRequest} from "next/server";
import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ slug: string }> },
): Promise<NextResponse> {
  const { slug } = await params
  const { searchParams } = new URL(req.url)
  const limit = searchParams.get("limit") ?? "12"

  try {
    const res = await backendFetch(
      `/mova/movies/${encodeURIComponent(slug)}/similar?limit=${encodeURIComponent(limit)}`,
      { cache: "no-store" },
    )
    const data: unknown = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: BACKEND_DOWN }, { status: 503 })
  }
}
