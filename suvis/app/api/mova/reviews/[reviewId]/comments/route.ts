import type { NextRequest} from "next/server";
import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

type RouteContext = { params: Promise<{ reviewId: string }> }

export async function GET(_req: NextRequest, { params }: RouteContext): Promise<NextResponse> {
  const { reviewId } = await params
  try {
    const res = await backendFetch(`/mova/reviews/${encodeURIComponent(reviewId)}/comments`, {
      cache: "no-store",
    })
    const data: unknown = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: BACKEND_DOWN }, { status: 502 })
  }
}

export async function POST(req: NextRequest, { params }: RouteContext): Promise<NextResponse> {
  const { reviewId } = await params
  const auth = req.headers.get("authorization")
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ detail: "잘못된 요청 본문입니다." }, { status: 400 })
  }
  try {
    const res = await backendFetch(`/mova/reviews/${encodeURIComponent(reviewId)}/comments`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(auth ? { Authorization: auth } : {}),
      },
      body: JSON.stringify(body),
    })
    const data: unknown = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: BACKEND_DOWN }, { status: 502 })
  }
}
