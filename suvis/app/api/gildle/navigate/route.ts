import type { NextRequest} from "next/server";
import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const res = await backendFetch("/api/gildle/navigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      return NextResponse.json(
        { error: `Backend ${res.status}` },
        { status: res.status },
      )
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ error: BACKEND_DOWN }, { status: 502 })
  }
}
