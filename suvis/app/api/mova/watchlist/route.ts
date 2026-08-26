import type { NextRequest} from "next/server";
import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

export async function POST(req: NextRequest): Promise<NextResponse> {
  const auth = req.headers.get("authorization")
  try {
    const body: unknown = await req.json()
    const res = await backendFetch("/mova/watchlist", {
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
    return NextResponse.json({ detail: BACKEND_DOWN }, { status: 503 })
  }
}
