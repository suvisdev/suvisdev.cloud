import { NextResponse } from "next/server"
import { backendFetch, BACKEND_DOWN } from "@/lib/backend-client"

export async function GET() {
  try {
    const res = await backendFetch("/api/gildle/graph-edges")
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
